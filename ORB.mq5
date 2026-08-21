//+------------------------------------------------------------------+
//| ORB.mq5                                                          |
//| Opening range breakout.                                          |
//|                                                                  |
//| Builds a high/low range over a window that starts at a fixed wall |
//| clock time in a chosen city, then trades the break of it.         |
//|                                                                  |
//| Session times resolve through TimeZones.mqh, so the range opens   |
//| at the same local moment year round and the host clock is never   |
//| consulted. Identical results on Windows and on Wine.              |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>
#include <TimeZones.mqh>

enum ENUM_ENTRY_MODE
  {
   ENTRY_MARKET_ON_CLOSE,  // signal bar closes past the level -> market
   ENTRY_STOP_AT_LEVEL,    // stop order resting at the level
   ENTRY_LIMIT_RETEST      // close past the level -> limit back at it
  };

enum ENUM_SL_MODE
  {
   SL_PERCENT_OF_RANGE,    // 50 = midpoint, 100 = opposite side, 0 = at the level
   SL_FIXED_POINTS
  };

enum ENUM_TP_MODE
  {
   TP_RR,
   TP_FIXED_POINTS,
   TP_RANGE_MULTIPLE,
   TP_NONE
  };

enum ENUM_LOT_MODE
  {
   LOT_FIXED,
   LOT_RISK_PERCENT
  };

input group                 "Session"
input ENUM_SESSION_TZ  InpTimeZone        = TZ_UTC;        // Session timezone
input int              InpStartHour       = 0;             // Session start hour (in that zone)
input int              InpStartMinute     = 0;             // Session start minute
input int              InpRangeMinutes    = 15;            // Range length (minutes)
input ENUM_TIMEFRAMES  InpSignalTF        = PERIOD_M1;     // Signal timeframe
input int              InpNoEntryAfterMin = 15;            // No entry after (min from range close, 0=off)
input int              InpForceCloseMin   = 360;           // Force close all (min from range close, 0=off)
input int              InpMaxHoldMinutes  = 60;            // Max hold per position (min from its fill, 0=off)

input group                 "Broker time"
input int              InpWinterOffset    = 2;             // Broker winter offset (hours ahead of UTC)
input bool             InpFollowsUSDST    = true;          // Broker uses US DST dates (false = EU)

input group                 "Entry"
input ENUM_ENTRY_MODE  InpEntryMode       = ENTRY_MARKET_ON_CLOSE;  // Entry mode
input int              InpMaxTradesPerDay = 1;             // Max trades per day
input double           InpMaxSpreadPoints = 0;             // Max spread (points, 0=off)
input double           InpMinRangePoints  = 0;             // Min range size (points, 0=off)
input double           InpMaxRangePoints  = 0;             // Max range size (points, 0=off)
input bool             InpTradeMon        = true;          // Trade Monday
input bool             InpTradeTue        = true;          // Trade Tuesday
input bool             InpTradeWed        = true;          // Trade Wednesday
input bool             InpTradeThu        = true;          // Trade Thursday
input bool             InpTradeFri        = true;          // Trade Friday

input group                 "Stop loss"
input ENUM_SL_MODE     InpSLMode          = SL_PERCENT_OF_RANGE;    // SL mode
input double           InpSLPercentOfRange= 50.0;          // SL percent of range (50=midpoint, 100=far side)
input double           InpSLFixedPoints   = 0;             // SL fixed distance (points)

input group                 "Stop management"
input double           InpStopMoveAtR     = 0.5;           // Move stop when trade reaches (R, 0=off)
input double           InpStopMoveToR     = -0.5;          // Move stop to (R: 0=entry, -0.5=half risk left)

input group                 "Take profit"
input ENUM_TP_MODE     InpTPMode          = TP_RR;         // TP mode
input double           InpRR              = 2.0;           // Reward:risk multiple
input double           InpTPFixedPoints   = 0;             // TP fixed distance (points)
input double           InpTPRangeMultiple = 1.0;           // TP as multiple of range size

input group                 "Risk"
input ENUM_LOT_MODE    InpLotMode         = LOT_RISK_PERCENT;       // Lot sizing mode
input double           InpLots            = 0.01;          // Fixed lot size
input double           InpRiskPercent     = 2.0;           // Risk per trade (percent of balance)
input double           InpMaxDailyLossPct = 3.5;           // Stop opening trades once down this much today (0=off)
input long             InpMagic           = 20260821;      // Magic number

input group                 "Analysis"
input bool             InpWriteCsv        = true;          // Write one CSV row per trade (Common\\Files)

CTrade   g_trade;
double   g_point;
int      g_digits;

//--- session state. Every field is rebuilt from history, never trusted
//--- across a restart. See RefreshSession().
datetime g_sessionStart = 0;
datetime g_rangeEnd     = 0;
double   g_rangeHigh    = 0;
double   g_rangeLow     = 0;
bool     g_rangeReady   = false;
bool     g_daySkipped   = false;
datetime g_lastSignalBar= 0;

//--- CSV trade log. Written to the terminal's Common\Files so the path is
//--- the same under the tester, live, Windows and Wine.
int      g_csv          = INVALID_HANDLE;
ulong    g_openTicket   = 0;      // position we are waiting to see close
double   g_openRange    = 0;      // its context, captured at entry
double   g_openSpread   = 0;
double   g_openRisk     = 0;
double   g_openEntry    = 0;
double   g_openSL       = 0;
bool     g_openIsBuy    = false;
datetime g_openTime     = 0;
int      g_openMinsLate = 0;      // minutes from range close to the entry

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpRangeMinutes <= 0)
     {
      Print("RangeMinutes must be positive");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpStartHour < 0 || InpStartHour > 23 || InpStartMinute < 0 || InpStartMinute > 59)
     {
      Print("session start is not a valid wall clock time");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpLotMode == LOT_RISK_PERCENT && InpRiskPercent <= 0)
     {
      Print("RiskPercent must be positive");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpSLMode == SL_FIXED_POINTS && InpSLFixedPoints <= 0)
     {
      Print("SLFixedPoints must be positive in that SL mode");
      return INIT_PARAMETERS_INCORRECT;
     }

   g_point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   g_digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetMarginMode();

   if(InpWriteCsv)
     {
      const string name = StringFormat("ORB_%s_%I64d.csv", _Symbol, InpMagic);
      g_csv = FileOpen(name, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
      if(g_csv == INVALID_HANDLE)
         PrintFormat("could not open %s for writing: %d", name, GetLastError());
      else
         FileWrite(g_csv, "entry_time", "range_pts", "spread_pts", "mins_after_range",
                          "dir", "entry", "sl", "risk_money", "profit_money", "R", "exit");
     }

   // A recompile reloads the EA mid-session and wipes everything above.
   // Rebuild immediately rather than waiting for the next tick, so a
   // reload during the range window cannot lose the range.
   RefreshSession(TimeCurrent());
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_csv != INVALID_HANDLE)
     {
      FileClose(g_csv);
      g_csv = INVALID_HANDLE;
     }
  }

//+------------------------------------------------------------------+
//| A tracked position has closed: pull its realised result from the  |
//| deal history and write the row. Called every tick, but does work  |
//| only on the tick after a close.                                   |
//+------------------------------------------------------------------+
void FlushClosedTrade()
  {
   if(g_openTicket == 0)
      return;
   if(PositionSelectByTicket(g_openTicket))
      return;                       // still open

   double profit = 0;
   string exit   = "";
   if(HistorySelectByPosition(g_openTicket))
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         const ulong t = HistoryDealGetTicket(i);
         if(t == 0)
            continue;
         profit += HistoryDealGetDouble(t, DEAL_PROFIT)
                 + HistoryDealGetDouble(t, DEAL_COMMISSION)
                 + HistoryDealGetDouble(t, DEAL_SWAP);
         if(HistoryDealGetInteger(t, DEAL_ENTRY) == DEAL_ENTRY_OUT && exit == "")
            exit = HistoryDealGetString(t, DEAL_COMMENT);
        }

   if(g_csv != INVALID_HANDLE && g_openRisk > 0)
      FileWrite(g_csv,
                TimeToString(g_openTime, TIME_DATE|TIME_MINUTES),
                DoubleToString(g_openRange, 0),
                DoubleToString(g_openSpread, 0),
                IntegerToString(g_openMinsLate),
                g_openIsBuy ? "buy" : "sell",
                DoubleToString(g_openEntry, g_digits),
                DoubleToString(g_openSL, g_digits),
                DoubleToString(g_openRisk, 2),
                DoubleToString(profit, 2),
                DoubleToString(profit / g_openRisk, 3),
                exit);

   g_openTicket = 0;
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   const datetime now = TimeCurrent();

   FlushClosedTrade();

   RefreshSession(now);
   if(g_daySkipped)
      return;

   ManageOpenPosition();
   CloseExpiredPositions(now);

   if(InpForceCloseMin > 0 && now >= g_rangeEnd + InpForceCloseMin * 60)
     {
      CloseEverything("force close");
      return;
     }

   if(!g_rangeReady)
     {
      if(now >= g_rangeEnd)
         BuildRange();
      return;
     }

   if(CountTradesToday() >= InpMaxTradesPerDay)
      return;
   if(InpEntryMode == ENTRY_STOP_AT_LEVEL)
      return;  // orders already rest at the levels

   LookForBreak();
  }

//+------------------------------------------------------------------+
//| Detect the session rollover and reset state.                     |
//|                                                                  |
//| Derived entirely from the clock and history, so it produces the   |
//| same answer whether the EA has been running all day or was just   |
//| dropped on the chart.                                            |
//+------------------------------------------------------------------+
void RefreshSession(const datetime now)
  {
   const datetime start = SessionStartInBrokerTime(now, InpTimeZone,
                                                   InpStartHour, InpStartMinute,
                                                   InpWinterOffset, InpFollowsUSDST);
   if(start == g_sessionStart)
      return;

   g_sessionStart  = start;
   g_rangeEnd      = start + InpRangeMinutes * 60;
   g_rangeHigh     = 0;
   g_rangeLow      = 0;
   g_rangeReady    = false;
   g_lastSignalBar = 0;
   g_daySkipped    = !IsTradingDay(start);

   CancelPendingOrders();  // anything left resting from yesterday

   PrintFormat("session %s -> range closes %s%s",
               TimeToString(g_sessionStart, TIME_DATE|TIME_MINUTES),
               TimeToString(g_rangeEnd, TIME_DATE|TIME_MINUTES),
               g_daySkipped ? "  [skipped: day of week]" : "");

   // Mid-session attach: the range window may already be behind us.
   if(!g_daySkipped && now >= g_rangeEnd)
      BuildRange();
  }

//+------------------------------------------------------------------+
bool IsTradingDay(const datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   switch(dt.day_of_week)
     {
      case 1: return InpTradeMon;
      case 2: return InpTradeTue;
      case 3: return InpTradeWed;
      case 4: return InpTradeThu;
      case 5: return InpTradeFri;
     }
   return false;  // weekend
  }

//+------------------------------------------------------------------+
//| Build the range from closed M1 bars.                             |
//|                                                                  |
//| Read from history rather than accumulated tick by tick, so a      |
//| restart mid-session reproduces it exactly and the tester and live |
//| agree.                                                           |
//+------------------------------------------------------------------+
void BuildRange()
  {
   MqlRates bars[];
   const int n = CopyRates(_Symbol, PERIOD_M1, g_sessionStart, g_rangeEnd - 1, bars);
   if(n <= 0)
     {
      // Holiday, session break, or history not loaded this far back.
      // Skip the day rather than inventing a range from whatever is there.
      g_daySkipped = true;
      PrintFormat("no M1 bars in the range window %s..%s — day skipped",
                  TimeToString(g_sessionStart, TIME_DATE|TIME_MINUTES),
                  TimeToString(g_rangeEnd, TIME_DATE|TIME_MINUTES));
      return;
     }

   g_rangeHigh = bars[0].high;
   g_rangeLow  = bars[0].low;
   for(int i = 1; i < n; i++)
     {
      g_rangeHigh = MathMax(g_rangeHigh, bars[i].high);
      g_rangeLow  = MathMin(g_rangeLow,  bars[i].low);
     }

   const double sizePoints = (g_rangeHigh - g_rangeLow) / g_point;
   if(InpMinRangePoints > 0 && sizePoints < InpMinRangePoints)
     {
      g_daySkipped = true;
      PrintFormat("range %.0f pts below minimum %.0f — day skipped", sizePoints, InpMinRangePoints);
      return;
     }
   if(InpMaxRangePoints > 0 && sizePoints > InpMaxRangePoints)
     {
      g_daySkipped = true;
      PrintFormat("range %.0f pts above maximum %.0f — day skipped", sizePoints, InpMaxRangePoints);
      return;
     }

   g_rangeReady = true;
   PrintFormat("range %s / %s  (%.0f pts, %d bars)",
               DoubleToString(g_rangeHigh, g_digits),
               DoubleToString(g_rangeLow,  g_digits),
               sizePoints, n);

   if(InpEntryMode == ENTRY_STOP_AT_LEVEL)
      PlaceStopOrders();
  }

//+------------------------------------------------------------------+
//| Watch closed signal bars for a break. Bar 0 is still forming and  |
//| is never consulted.                                              |
//|                                                                  |
//| The entry deadline is tested against the bar's own open time, not |
//| against the current clock. A bar stamped 00:59 only closes at     |
//| 01:00:00, so a wall-clock cutoff at 01:00 would discard the last  |
//| eligible bar. With a 15 minute range from 00:00 and a 45 minute   |
//| deadline, 00:59 is the final bar that can trade and 01:00 is out. |
//+------------------------------------------------------------------+
void LookForBreak()
  {
   MqlRates bars[];
   if(CopyRates(_Symbol, InpSignalTF, 1, 1, bars) != 1)
      return;
   if(bars[0].time <= g_lastSignalBar || bars[0].time < g_rangeEnd)
      return;
   if(InpNoEntryAfterMin > 0 && bars[0].time >= g_rangeEnd + InpNoEntryAfterMin * 60)
      return;
   g_lastSignalBar = bars[0].time;

   if(bars[0].close > g_rangeHigh)
      Enter(ORDER_TYPE_BUY);
   else if(bars[0].close < g_rangeLow)
      Enter(ORDER_TYPE_SELL);
  }

//+------------------------------------------------------------------+
void Enter(const ENUM_ORDER_TYPE dir)
  {
   if(!SpreadIsAcceptable())
      return;
   if(DailyLossExceeded())
      return;

   const bool   isBuy = (dir == ORDER_TYPE_BUY);
   const double level = isBuy ? g_rangeHigh : g_rangeLow;
   const double sl    = StopLossFor(isBuy, level);

   if(InpEntryMode == ENTRY_LIMIT_RETEST)
     {
      // A pending order fills at its own price, so that price is both
      // the sizing basis and the anchor for the target.
      const double price = NormalizeDouble(level, g_digits);
      const double lots  = LotsFor(price, sl);
      if(lots <= 0)
         return;

      const double tp = TakeProfitFrom(isBuy, price, sl);
      if(!(isBuy ? g_trade.BuyLimit(lots, price, _Symbol, sl, tp)
                 : g_trade.SellLimit(lots, price, _Symbol, sl, tp)))
         PrintFormat("limit order rejected: %d %s", g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return;
     }

   // Market entry. Size from the price we are about to pay, not from
   // the range level: the breakout candle closed somewhere past the
   // level, so the real stop distance is wider and sizing off the level
   // risks more than the configured percent on every single trade.
   const double entry = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                              : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   const double lots  = LotsFor(entry, sl);
   if(lots <= 0)
      return;

   // The stop is structural, so it ships with the order. The target has
   // to wait for the fill.
   if(!(isBuy ? g_trade.Buy(lots, _Symbol, 0, sl, 0)
              : g_trade.Sell(lots, _Symbol, 0, sl, 0)))
     {
      PrintFormat("market order rejected: %d %s", g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return;
     }

   const double fill = g_trade.ResultPrice();
   AnchorTakeProfitToFill(fill, isBuy, sl);

   // Capture the context this trade was taken in, so FlushClosedTrade can
   // pair it with the realised result once the position closes. Without
   // this the range size is unrecoverable after the run.
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol ||
         PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      g_openTicket   = t;
      g_openRange    = (g_rangeHigh - g_rangeLow) / g_point;
      g_openSpread   = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / g_point;
      g_openRisk     = RiskOf(lots, fill, sl);
      g_openEntry    = fill;
      g_openSL       = sl;
      g_openIsBuy    = isBuy;
      g_openTime     = TimeCurrent();
      g_openMinsLate = (int)((TimeCurrent() - g_rangeEnd) / 60);
      break;
     }

   // Spread is logged as a share of the money at risk, because that is
   // the form the cost actually takes: a fixed spread against a stop
   // distance set by the day's range. MT5 keeps no spread column in the
   // deals table, so without this the drag is unmeasurable after the run.
   const double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   const double risk    = RiskOf(lots, fill, sl);
   const double spread  = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(fill > 0 && balance > 0 && risk > 0)
      PrintFormat("%s %.2f lots at %s, stop %s, risk %.2f%% of balance, "
                  "range %.0f pts, spread %.0f pts = %.1f%% of risk",
                  isBuy ? "buy" : "sell", lots,
                  DoubleToString(fill, g_digits), DoubleToString(sl, g_digits),
                  100.0 * risk / balance,
                  (g_rangeHigh - g_rangeLow) / g_point,
                  spread / g_point,
                  100.0 * RiskOf(lots, fill + (isBuy ? spread : -spread), fill) / risk);
  }

//+------------------------------------------------------------------+
//| Account-wide daily loss guard.                                    |
//|                                                                   |
//| A prop firm's daily limit counts every trade on the account, so    |
//| this sums all deals since broker midnight regardless of magic,     |
//| plus open floating P&L, and compares against the balance the day   |
//| started with. Several instances of this EA on different sessions   |
//| cannot see each other's trades, which is exactly how an account    |
//| breaches the limit on the third trade of the day.                  |
//|                                                                   |
//| It blocks opening new risk. It never closes anything — the limit   |
//| is about what you put on, and force-closing into a loss locks it   |
//| in for no benefit.                                                 |
//+------------------------------------------------------------------+
bool DailyLossExceeded()
  {
   if(InpMaxDailyLossPct <= 0)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;
   const datetime dayStart = StructToTime(dt);

   double realized = 0;
   if(HistorySelect(dayStart, TimeCurrent() + 1))
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         const ulong t = HistoryDealGetTicket(i);
         if(t == 0)
            continue;
         realized += HistoryDealGetDouble(t, DEAL_PROFIT)
                   + HistoryDealGetDouble(t, DEAL_COMMISSION)
                   + HistoryDealGetDouble(t, DEAL_SWAP);
        }

   double floating = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t))
         continue;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }

   const double openingBalance = AccountInfoDouble(ACCOUNT_BALANCE) - realized;
   if(openingBalance <= 0)
      return false;

   const double lossPct = -100.0 * (realized + floating) / openingBalance;
   if(lossPct < InpMaxDailyLossPct)
      return false;

   PrintFormat("down %.2f%% today, limit %.2f%% — no new trades", lossPct, InpMaxDailyLossPct);
   return true;
  }

//+------------------------------------------------------------------+
//| Money at risk if the stop is hit, for the given size.            |
//+------------------------------------------------------------------+
double RiskOf(const double lots, const double entry, const double sl)
  {
   const double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   const double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0)
      return 0;
   return MathAbs(entry - sl) / tickSize * tickValue * lots;
  }

//+------------------------------------------------------------------+
//| Set the target once the fill price is known, measuring R from the |
//| fill to the stop rather than from the range level. Without this,  |
//| RR=2 produces whatever ratio the breakout gap happened to leave.  |
//+------------------------------------------------------------------+
void AnchorTakeProfitToFill(const double fill, const bool isBuy, const double sl)
  {
   if(InpTPMode == TP_NONE || fill <= 0)
      return;

   const double tp = TakeProfitFrom(isBuy, fill, sl);
   if(tp <= 0)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      if(!g_trade.PositionModify(ticket, sl, tp))
         PrintFormat("could not set target on #%I64u: %d %s", ticket,
                     g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return;
     }
  }

//+------------------------------------------------------------------+
void PlaceStopOrders()
  {
   if(!SpreadIsAcceptable())
      return;

   const double slBuy  = StopLossFor(true,  g_rangeHigh);
   const double slSell = StopLossFor(false, g_rangeLow);
   // Stop orders fill at the level, so the level is the anchor.
   const double tpBuy  = TakeProfitFrom(true,  g_rangeHigh, slBuy);
   const double tpSell = TakeProfitFrom(false, g_rangeLow,  slSell);
   const double lotBuy = LotsFor(g_rangeHigh, slBuy);
   const double lotSell= LotsFor(g_rangeLow,  slSell);

   if(lotBuy > 0)
      g_trade.BuyStop(lotBuy, NormalizeDouble(g_rangeHigh, g_digits), _Symbol, slBuy, tpBuy);
   if(lotSell > 0)
      g_trade.SellStop(lotSell, NormalizeDouble(g_rangeLow, g_digits), _Symbol, slSell, tpSell);
  }

//+------------------------------------------------------------------+
double StopLossFor(const bool isBuy, const double level)
  {
   double distance;
   if(InpSLMode == SL_FIXED_POINTS)
      distance = InpSLFixedPoints * g_point;
   else
      distance = (g_rangeHigh - g_rangeLow) * (InpSLPercentOfRange / 100.0);

   if(distance <= 0)
      return 0;

   const double sl = isBuy ? level - distance : level + distance;
   return NormalizeDouble(sl, g_digits);
  }

//+------------------------------------------------------------------+
//| `anchor` is the price the trade actually enters at. In RR mode the |
//| risk is the anchor-to-stop distance, so RR is the ratio you get.   |
double TakeProfitFrom(const bool isBuy, const double anchor, const double sl)
  {
   double distance = 0;
   switch(InpTPMode)
     {
      case TP_NONE:           return 0;
      case TP_FIXED_POINTS:   distance = InpTPFixedPoints * g_point;                     break;
      case TP_RANGE_MULTIPLE: distance = (g_rangeHigh - g_rangeLow) * InpTPRangeMultiple; break;
      case TP_RR:             distance = MathAbs(anchor - sl) * InpRR;                   break;
     }
   if(distance <= 0)
      return 0;

   const double tp = isBuy ? anchor + distance : anchor - distance;
   return NormalizeDouble(tp, g_digits);
  }

//+------------------------------------------------------------------+
//| Position size. In risk mode, solve for the lot count whose loss   |
//| at the stop equals the configured share of the balance.          |
//|                                                                  |
//| `entry` must be the price the trade actually opens at, not the    |
//| range level, or realised risk exceeds InpRiskPercent by however   |
//| far the breakout ran past the level.                             |
//+------------------------------------------------------------------+
double LotsFor(const double entry, const double sl)
  {
   double lots = InpLots;

   if(InpLotMode == LOT_RISK_PERCENT)
     {
      if(sl == 0)
        {
         Print("risk sizing needs a stop loss — no trade");
         return 0;
        }
      const double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      const double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tickValue <= 0 || tickSize <= 0)
        {
         Print("symbol has no tick value — no trade");
         return 0;
        }
      const double riskAmount = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
      const double lossPerLot = MathAbs(entry - sl) / tickSize * tickValue;
      if(lossPerLot <= 0)
         return 0;
      lots = riskAmount / lossPerLot;
     }

   const double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   const double min  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   const double max  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   lots = MathFloor(lots / step) * step;
   lots = MathMin(lots, max);

   if(lots < min)
     {
      PrintFormat("computed %.4f lots, below the %.4f minimum — no trade", lots, min);
      return 0;
     }
   return lots;
  }

//+------------------------------------------------------------------+
bool SpreadIsAcceptable()
  {
   if(InpMaxSpreadPoints <= 0)
      return true;

   const double spread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) -
                          SymbolInfoDouble(_Symbol, SYMBOL_BID)) / g_point;
   if(spread > InpMaxSpreadPoints)
     {
      PrintFormat("spread %.0f pts over the %.0f limit — skipped", spread, InpMaxSpreadPoints);
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Once price has travelled InpStopMoveAtR multiples of the original |
//| risk, move the stop to InpStopMoveToR. The destination is signed:  |
//| 0 is entry, negative leaves part of the risk on the table.        |
//|                                                                   |
//|   AtR 0.5, ToR -0.5  ->  at +0.5R the stop halves the loss        |
//|   AtR 1.0, ToR  0.0  ->  classic breakeven at 1R                  |
//|                                                                   |
//| The stop is only ever tightened, never loosened.                  |
//+------------------------------------------------------------------+
void ManageOpenPosition()
  {
   if(InpStopMoveAtR <= 0)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      const double open = PositionGetDouble(POSITION_PRICE_OPEN);
      const double sl   = PositionGetDouble(POSITION_SL);
      const double tp   = PositionGetDouble(POSITION_TP);
      if(sl == 0)
         continue;

      const bool   isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      const double risk  = MathAbs(open - sl);
      const double price = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                 : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      const double moved = isBuy ? price - open : open - price;

      if(moved < risk * InpStopMoveAtR)
         continue;

      const double target = isBuy ? open + risk * InpStopMoveToR
                                  : open - risk * InpStopMoveToR;
      const double newSL  = NormalizeDouble(target, g_digits);

      if(isBuy ? newSL <= sl : newSL >= sl)
         continue;  // already at least this tight

      if(!g_trade.PositionModify(ticket, newSL, tp))
         PrintFormat("could not move stop on #%I64u: %d %s", ticket,
                     g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
//| Hard cap on how long a single position may stay open, measured    |
//| from its own fill. ForceCloseMin cannot do this job: it counts     |
//| from the range close, and an entry may arrive up to               |
//| NoEntryAfterMin later, so the same deadline allows very different  |
//| holding times depending on when the break happened.               |
//+------------------------------------------------------------------+
void CloseExpiredPositions(const datetime now)
  {
   if(InpMaxHoldMinutes <= 0)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      const datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      if(now - opened < InpMaxHoldMinutes * 60)
         continue;

      PrintFormat("closing #%I64u: held %d minutes", ticket, (int)((now - opened) / 60));
      g_trade.PositionClose(ticket);
     }
  }

//+------------------------------------------------------------------+
//| Trades opened today, counted from history rather than a variable, |
//| so the limit survives a reload.                                  |
//+------------------------------------------------------------------+
int CountTradesToday()
  {
   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         (datetime)PositionGetInteger(POSITION_TIME) >= g_sessionStart)
         count++;
     }

   if(!HistorySelect(g_sessionStart, TimeCurrent() + 1))
      return count;

   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL) != _Symbol)
         continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC) != InpMagic)
         continue;
      if(HistoryDealGetInteger(ticket, DEAL_ENTRY) == DEAL_ENTRY_IN)
         count++;
     }
   return count;
  }

//+------------------------------------------------------------------+
void CancelPendingOrders()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         OrderGetInteger(ORDER_MAGIC) == InpMagic)
         g_trade.OrderDelete(ticket);
     }
  }

//+------------------------------------------------------------------+
void CloseEverything(const string reason)
  {
   CancelPendingOrders();

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
        {
         PrintFormat("closing #%I64u: %s", ticket, reason);
         g_trade.PositionClose(ticket);
        }
     }
  }
//+------------------------------------------------------------------+
