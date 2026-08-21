//+------------------------------------------------------------------+
//| BarDump.mq5                                                      |
//| Research tool, not a strategy.                                   |
//|                                                                  |
//| Writes the M1 bars around the session window to CSV so parameter  |
//| sweeps can run offline. One backtest here replaces hundreds in    |
//| the Strategy Tester: entry timing depends only on the range       |
//| break, so SL distance, target and stop-move rules can all be      |
//| re-evaluated against the same recorded paths.                    |
//|                                                                  |
//| Run with Model=1 (1 minute OHLC). The M1 bars are historical      |
//| either way, so real ticks buy nothing and cost minutes.          |
//+------------------------------------------------------------------+
#property strict

input int InpFromHour = 2;   // first broker hour to record
input int InpToHour   = 5;   // last broker hour to record

int      g_csv  = INVALID_HANDLE;
datetime g_last = 0;

int OnInit()
  {
   const string name = StringFormat("bars_%s.csv", _Symbol);
   g_csv = FileOpen(name, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(g_csv == INVALID_HANDLE)
     {
      PrintFormat("cannot open %s: %d", name, GetLastError());
      return INIT_FAILED;
     }
   if(FileSize(g_csv) == 0)
      FileWrite(g_csv, "time", "open", "high", "low", "close");
   FileSeek(g_csv, 0, SEEK_END);
   PrintFormat("recording M1 bars, broker hours %d-%d, to %s", InpFromHour, InpToHour, name);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_csv != INVALID_HANDLE)
     {
      FileClose(g_csv);
      g_csv = INVALID_HANDLE;
     }
  }

void OnTick()
  {
   MqlRates b[];
   if(CopyRates(_Symbol, PERIOD_M1, 1, 1, b) != 1)   // last closed bar only
      return;
   if(b[0].time <= g_last)
      return;
   g_last = b[0].time;

   MqlDateTime dt;
   TimeToStruct(b[0].time, dt);
   if(dt.hour < InpFromHour || dt.hour > InpToHour)
      return;

   FileWrite(g_csv,
             TimeToString(b[0].time, TIME_DATE|TIME_MINUTES),
             DoubleToString(b[0].open,  _Digits),
             DoubleToString(b[0].high,  _Digits),
             DoubleToString(b[0].low,   _Digits),
             DoubleToString(b[0].close, _Digits));
  }
//+------------------------------------------------------------------+
