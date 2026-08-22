//+------------------------------------------------------------------+
//|                                                        Panel.mqh |
//|  On-chart control panel for ORB.                                 |
//|                                                                  |
//|  One toggle and five editable fields. The fields are locked       |
//|  unless trading is OFF *and* there is no open position.          |
//|                                                                  |
//|  Why both conditions: the stop-move logic recovers a trade's      |
//|  original risk from its take profit divided by RR. Change RR      |
//|  while a position is open and that recovery returns the wrong     |
//|  number, which moves the stop to the wrong price. Locking on      |
//|  "OFF and flat" removes the possibility rather than guarding      |
//|  against it. Turning trading off never abandons a live position:  |
//|  it stops new entries, management continues.                     |
//|                                                                  |
//|  Values persist in terminal globals, so recompiling or            |
//|  restarting does not silently reset your settings.               |
//+------------------------------------------------------------------+
#property strict

#define P_PFX  "ORBP_"          // object name prefix
#define P_X    14               // distance from the chart corner
#define P_Y    24
#define P_W    276
#define P_ROW  26

// The host EA declares g_tradingOn, g_lotMode, g_riskPercent, g_riskMoney,
// g_rr, g_moveAtR and g_moveToR before including this file, and the panel
// writes to those same variables directly. No forward declarations: MQL5's
// `extern` would risk creating separate copies, and then edits here would
// never reach the trading logic.

//--- field identity. Order drives layout, so adding one is a single line.
//--- Row order drives layout. KIND decides whether a row is an edit box or a
//    button, so adding a setting is one enum entry plus one case per accessor.
enum ENUM_P_FIELD
  {
   P_RISK, P_RR, P_START, P_RANGE, P_WINDOW, P_STOPMOVE, P_MOVEAT, P_MOVETO, P_FIELDS
  };

string g_pStatus  = "";
bool   g_pVisible = false;
long   g_pMagic   = 0;

//+------------------------------------------------------------------+
//| Terminal globals, so settings survive a restart. Keyed by symbol |
//| and magic so two charts running ORB do not overwrite each other. |
//+------------------------------------------------------------------+
string PStoreKey(const string field)
  {
   return StringFormat("ORB_%s_%I64d_%s", _Symbol, g_pMagic, field);
  }

//| The tester shares terminal globals with the live terminal, so loading or
//| saving there would let a live toggle leak into a backtest and silently
//| change what it measures. Both are no-ops unless the panel really exists.
bool PStoreActive() { return g_pVisible && !MQLInfoInteger(MQL_TESTER); }

void PStoreSave()
  {
   if(!PStoreActive())
      return;
   GlobalVariableSet(PStoreKey("on"),       g_tradingOn ? 1 : 0);
   GlobalVariableSet(PStoreKey("lotmode"),  (double)g_lotMode);
   GlobalVariableSet(PStoreKey("riskpct"),  g_riskPercent);
   GlobalVariableSet(PStoreKey("riskmoney"),g_riskMoney);
   GlobalVariableSet(PStoreKey("rr"),       g_rr);
   GlobalVariableSet(PStoreKey("moveat"),   g_moveAtR);
   GlobalVariableSet(PStoreKey("moveto"),   g_moveToR);
   GlobalVariableSet(PStoreKey("smove"),    g_stopMoveOn ? 1 : 0);
   GlobalVariableSet(PStoreKey("sh"),       (double)g_startHour);
   GlobalVariableSet(PStoreKey("sm"),       (double)g_startMinute);
   GlobalVariableSet(PStoreKey("rangemin"), (double)g_rangeMinutes);
   GlobalVariableSet(PStoreKey("window"),   (double)g_noEntryAfterMin);
  }

//| Restore only what was actually stored, so a fresh chart uses the
//| inputs and an existing one keeps whatever you last set.
void PStoreLoad()
  {
   if(!PStoreActive())
      return;
   if(GlobalVariableCheck(PStoreKey("on")))        g_tradingOn   = GlobalVariableGet(PStoreKey("on")) > 0.5;
   if(GlobalVariableCheck(PStoreKey("lotmode")))   g_lotMode     = (ENUM_LOT_MODE)(int)GlobalVariableGet(PStoreKey("lotmode"));
   if(GlobalVariableCheck(PStoreKey("riskpct")))   g_riskPercent = GlobalVariableGet(PStoreKey("riskpct"));
   if(GlobalVariableCheck(PStoreKey("riskmoney"))) g_riskMoney   = GlobalVariableGet(PStoreKey("riskmoney"));
   if(GlobalVariableCheck(PStoreKey("rr")))        g_rr          = GlobalVariableGet(PStoreKey("rr"));
   if(GlobalVariableCheck(PStoreKey("moveat")))    g_moveAtR     = GlobalVariableGet(PStoreKey("moveat"));
   if(GlobalVariableCheck(PStoreKey("moveto")))    g_moveToR     = GlobalVariableGet(PStoreKey("moveto"));
   if(GlobalVariableCheck(PStoreKey("smove")))     g_stopMoveOn  = GlobalVariableGet(PStoreKey("smove")) > 0.5;
   if(GlobalVariableCheck(PStoreKey("sh")))        g_startHour   = (int)GlobalVariableGet(PStoreKey("sh"));
   if(GlobalVariableCheck(PStoreKey("sm")))        g_startMinute = (int)GlobalVariableGet(PStoreKey("sm"));
   if(GlobalVariableCheck(PStoreKey("rangemin")))  g_rangeMinutes = (int)GlobalVariableGet(PStoreKey("rangemin"));
   if(GlobalVariableCheck(PStoreKey("window")))    g_noEntryAfterMin = (int)GlobalVariableGet(PStoreKey("window"));
  }

//+------------------------------------------------------------------+
//| Object helpers                                                   |
//+------------------------------------------------------------------+
void PLabel(const string name, const int x, const int y, const string text,
            const color clr, const int size = 8, const string font = "Tahoma")
  {
   const string n = P_PFX + name;
   if(ObjectFind(0, n) < 0)
      ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetString(0, n, OBJPROP_FONT, font);
   ObjectSetString(0, n, OBJPROP_TEXT, text);
  }

void PBox(const string name, const int x, const int y, const int w, const int h,
          const color bg, const color border)
  {
   const string n = P_PFX + name;
   if(ObjectFind(0, n) < 0)
      ObjectCreate(0, n, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, n, OBJPROP_COLOR, border);
   ObjectSetInteger(0, n, OBJPROP_BACK, false);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
  }

void PButton(const string name, const int x, const int y, const int w, const int h,
             const string text, const color bg, const color fg)
  {
   const string n = P_PFX + name;
   if(ObjectFind(0, n) < 0)
      ObjectCreate(0, n, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_COLOR, fg);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, n, OBJPROP_BORDER_COLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_STATE, false);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetString(0, n, OBJPROP_FONT, "Tahoma");
   ObjectSetString(0, n, OBJPROP_TEXT, text);
  }

void PEdit(const string name, const int x, const int y, const int w, const int h,
           const string text, const bool editable)
  {
   const string n = P_PFX + name;
   if(ObjectFind(0, n) < 0)
      ObjectCreate(0, n, OBJ_EDIT, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_ALIGN, ALIGN_RIGHT);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, editable ? C'34,32,28' : C'22,21,19');
   ObjectSetInteger(0, n, OBJPROP_COLOR,   editable ? C'243,239,231' : C'110,105,98');
   ObjectSetInteger(0, n, OBJPROP_BORDER_COLOR, editable ? C'201,168,106' : C'45,42,38');
   ObjectSetInteger(0, n, OBJPROP_READONLY, !editable);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetString(0, n, OBJPROP_FONT, "Consolas");
   ObjectSetString(0, n, OBJPROP_TEXT, text);
  }

//+------------------------------------------------------------------+
//| Field metadata: label, object suffix, and the accepted range.    |
//+------------------------------------------------------------------+
string PFieldName(const int f)
  {
   switch(f)
     {
      case P_RISK:     return "risk";
      case P_RR:       return "rr";
      case P_START:    return "start";
      case P_RANGE:    return "range";
      case P_WINDOW:   return "window";
      case P_STOPMOVE: return "stopmove";
      case P_MOVEAT:   return "moveat";
      case P_MOVETO:   return "moveto";
     }
   return "";
  }

//| A row is either an edit box or a plain toggle button.
bool PFieldIsToggle(const int f) { return f == P_STOPMOVE; }

string PFieldLabel(const int f)
  {
   switch(f)
     {
      case P_RISK:     return (g_lotMode == LOT_RISK_MONEY) ? "Risk per trade (cash)"
                                                            : "Risk per trade (compounds)";
      case P_RR:       return "Reward : risk";
      case P_START:    return "Session start";
      case P_RANGE:    return "Range length";
      case P_WINDOW:   return "Break window";
      case P_STOPMOVE: return "Stop move";
      case P_MOVEAT:   return "   move at";
      case P_MOVETO:   return "   move to";
     }
   return "";
  }

//| Suffix after the value, so the units are never ambiguous.
string PFieldUnit(const int f)
  {
   switch(f)
     {
      case P_RISK:   return (g_lotMode == LOT_RISK_MONEY)
                            ? AccountInfoString(ACCOUNT_CURRENCY) : "%";
      case P_RR:     return "R";
      case P_START:  return "UTC";
      case P_RANGE:  return "min";
      case P_WINDOW: return "min";
      case P_MOVEAT: return "R";
      case P_MOVETO: return "R";
     }
   return "";
  }

//| What the box shows.
string PFieldText(const int f)
  {
   switch(f)
     {
      case P_RISK:   return (g_lotMode == LOT_RISK_MONEY)
                            ? DoubleToString(g_riskMoney, 0) : DoubleToString(g_riskPercent, 2);
      case P_RR:     return DoubleToString(g_rr, 2);
      case P_START:  return StringFormat("%02d:%02d", g_startHour, g_startMinute);
      case P_RANGE:  return IntegerToString(g_rangeMinutes);
      case P_WINDOW: return IntegerToString(g_noEntryAfterMin);
      case P_MOVEAT: return DoubleToString(g_moveAtR, 2);
      case P_MOVETO: return DoubleToString(g_moveToR, 2);
     }
   return "";
  }

//| Parse and apply. Returns false and says why rather than accepting nonsense.
bool PFieldApply(const int f, const string txt)
  {
   if(f == P_START)
     {
      string p[];
      if(StringSplit(txt, ':', p) != 2)
        { PrintFormat("panel: session start %s must look like HH:MM", txt); return false; }
      const int h = (int)StringToInteger(p[0]), m = (int)StringToInteger(p[1]);
      if(h < 0 || h > 23 || m < 0 || m > 59)
        { PrintFormat("panel: %s is not a valid time of day", txt); return false; }
      g_startHour = h; g_startMinute = m;
      Print("panel: session start changed - the new range is built on the next session, "
            "not retroactively");
      return true;
     }

   const double v = StringToDouble(txt);
   if(v == 0 && StringLen(txt) > 0 && StringGetCharacter(txt, 0) != '0')
     { PrintFormat("panel: %s is not a number", txt); return false; }

   switch(f)
     {
      case P_RISK:
         if(g_lotMode == LOT_RISK_MONEY)
           {
            if(v <= 0 || v > AccountInfoDouble(ACCOUNT_BALANCE))
              { PrintFormat("panel: risk %.2f must be above 0 and no more than the balance", v); return false; }
            g_riskMoney = v;
           }
         else
           {
            if(v <= 0 || v > 20)
              { PrintFormat("panel: risk %.2f%% must be between 0 and 20", v); return false; }
            g_riskPercent = v;
           }
         return true;
      case P_RR:
         if(v <= 0 || v > 20)
           { PrintFormat("panel: reward:risk %.2f must be between 0 and 20", v); return false; }
         g_rr = v; return true;
      case P_RANGE:
         if(v < 1 || v > 240)
           { PrintFormat("panel: range length %.0f must be between 1 and 240 minutes", v); return false; }
         g_rangeMinutes = (int)v;
         Print("panel: range length changed - applies from the next session");
         return true;
      case P_WINDOW:
         if(v < 0 || v > 240)
           { PrintFormat("panel: break window %.0f must be between 0 and 240 minutes (0 = no limit)", v); return false; }
         g_noEntryAfterMin = (int)v; return true;
      case P_MOVEAT:
         if(v <= 0 || v > 10)
           { PrintFormat("panel: move-at %.2f must be above 0 and no more than 10 "
                         "(use the Stop move button to switch it off)", v); return false; }
         if(g_moveToR >= v)
           { PrintFormat("panel: move-at %.2f must sit above move-to %.2f", v, g_moveToR); return false; }
         g_moveAtR = v; return true;
      case P_MOVETO:
         if(v < -1.0 || v > 5.0)
           { PrintFormat("panel: move-to %.2f must be between -1 and 5", v); return false; }
         if(v >= g_moveAtR)
           { PrintFormat("panel: move-to %.2f must sit below move-at %.2f, or the stop "
                         "would jump past price", v, g_moveAtR); return false; }
         g_moveToR = v; return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Fields are editable only while trading is OFF and flat.          |
//+------------------------------------------------------------------+
bool PHasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      const ulong t = PositionGetTicket(i);
      if(t == 0 || !PositionSelectByTicket(t))
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == g_pMagic)
         return true;
     }
   return false;
  }

bool PEditable() { return !g_tradingOn && !PHasPosition(); }

//| One place decides where the status line lives, so PanelDraw and
//| PanelSetStatus cannot disagree and make the text jump.
int PStatusY() { return P_Y + 60 + P_FIELDS * P_ROW; }

//+------------------------------------------------------------------+
//| Draw. Called on init and whenever anything changes.              |
//+------------------------------------------------------------------+
void PanelDraw()
  {
   if(!g_pVisible)
      return;

   const bool   edit = PEditable();
   const bool   pos  = PHasPosition();
   const int    h    = 96 + P_FIELDS * P_ROW;
   const color  ink  = C'243,239,231';
   const color  mut  = C'148,140,128';
   const color  acc  = C'201,168,106';
   const color  ok   = C'79,190,139';
   const color  no   = C'224,128,111';

   PBox("bg", P_X, P_Y, P_W, h, C'25,23,19', C'58,54,48');
   PLabel("title", P_X + 12, P_Y + 9, "ORB  " + _Symbol, ink, 9, "Tahoma Bold");

   PButton("toggle", P_X + P_W - 96, P_Y + 6, 84, 22,
           g_tradingOn ? "TRADING ON" : "TRADING OFF",
           g_tradingOn ? C'18,60,44' : C'62,26,22',
           g_tradingOn ? ok : no);

   int y = P_Y + 40;
   for(int f = 0; f < P_FIELDS; f++)
     {
      const string nm = PFieldName(f);
      // the two move rows are meaningless while the stop move is off
      const bool dim  = (!g_stopMoveOn && (f == P_MOVEAT || f == P_MOVETO));
      PLabel("l_" + nm, P_X + 12, y + 5, PFieldLabel(f), dim ? C'90,86,80' : mut, 8);

      if(PFieldIsToggle(f))
        {
         PButton("b_" + nm, P_X + 138, y, 74, 20, g_stopMoveOn ? "ON" : "OFF",
                 g_stopMoveOn ? C'18,60,44' : C'52,24,21',
                 g_stopMoveOn ? ok : no);
        }
      else
        {
         PEdit("e_" + nm, P_X + 138, y, 74, 20, PFieldText(f), edit && !dim);
         if(f == P_RISK)
            // the unit doubles as the mode switch: percent compounds, cash does not
            PButton("mode", P_X + 216, y, 40, 20, PFieldUnit(f),
                    edit ? C'40,37,31' : C'26,25,22', edit ? acc : mut);
         else
            PLabel("u_" + nm, P_X + 218, y + 5, PFieldUnit(f), dim ? C'90,86,80' : mut, 8);
        }
      y += P_ROW;
     }

   // why the fields look the way they do, rather than leaving you guessing
   string why;
   color  whyc;
   if(edit)          { why = "fields unlocked";                    whyc = acc; }
   else if(pos)      { why = "locked: position open";              whyc = no;  }
   else              { why = "locked: switch trading off to edit"; whyc = mut; }
   PLabel("lock", P_X + 12, P_Y + 44 + P_FIELDS * P_ROW, why, whyc, 8);

   PLabel("status", P_X + 12, PStatusY(), g_pStatus, mut, 8, "Consolas");
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Lifecycle                                                        |
//+------------------------------------------------------------------+
void PanelInit(const long magic, const bool show)
  {
   g_pMagic   = magic;
   // Drawing thousands of objects makes a non-visual backtest crawl and shows
   // nobody anything, so the panel simply does not exist there.
   g_pVisible = show && (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE));

   // Trading starts OFF so that attaching the EA never opens a position on its
   // own. That is only safe when there is a panel to switch it on: with no
   // panel -- a non-visual backtest, or InpShowPanel off -- nothing could ever
   // enable it and every run would take zero trades.
   if(!g_pVisible)
      g_tradingOn = true;

   PStoreLoad();
   PanelDraw();
  }

void PanelDeinit()
  {
   ObjectsDeleteAll(0, P_PFX);
   ChartRedraw();
  }

void PanelSetStatus(const string s)
  {
   if(!g_pVisible || s == g_pStatus)
      return;
   g_pStatus = s;
   PLabel("status", P_X + 12, PStatusY(), s, C'148,140,128', 8, "Consolas");
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Events. Returns true if the panel handled it.                    |
//+------------------------------------------------------------------+
bool PanelEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(!g_pVisible)
      return false;

   if(id == CHARTEVENT_OBJECT_CLICK && sparam == P_PFX "b_stopmove")
     {
      ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
      if(!PEditable())
        {
         Print("panel: locked - switch trading off and close any position first");
         PanelDraw();
         return true;
        }
      g_stopMoveOn = !g_stopMoveOn;
      PrintFormat("panel: stop move %s%s", g_stopMoveOn ? "ON" : "OFF",
                  g_stopMoveOn ? StringFormat(" (at +%.2fR move to %.2fR)", g_moveAtR, g_moveToR)
                               : " - the stop stays where it started");
      PStoreSave();
      PanelDraw();
      return true;
     }

   if(id == CHARTEVENT_OBJECT_CLICK && sparam == P_PFX "mode")
     {
      ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
      if(!PEditable())
        {
         Print("panel: locked - switch trading off and close any position first");
         PanelDraw();
         return true;
        }
      g_lotMode = (g_lotMode == LOT_RISK_MONEY) ? LOT_RISK_PERCENT : LOT_RISK_MONEY;
      PrintFormat("panel: risk mode %s (%s)",
                  g_lotMode == LOT_RISK_MONEY ? "fixed cash" : "percent of balance",
                  g_lotMode == LOT_RISK_MONEY
                  ? StringFormat("%.0f %s a trade, does not compound",
                                 g_riskMoney, AccountInfoString(ACCOUNT_CURRENCY))
                  : StringFormat("%.2f%% of the balance a trade, compounds", g_riskPercent));
      PStoreSave();
      PanelDraw();
      return true;
     }

   if(id == CHARTEVENT_OBJECT_CLICK && sparam == P_PFX "toggle")
     {
      g_tradingOn = !g_tradingOn;
      ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
      PrintFormat("panel: trading %s%s", g_tradingOn ? "ON" : "OFF",
                  (!g_tradingOn && PHasPosition())
                  ? " - no new entries; the open position is still managed" : "");
      PStoreSave();
      PanelDraw();
      return true;
     }

   if(id == CHARTEVENT_OBJECT_ENDEDIT)
     {
      for(int f = 0; f < P_FIELDS; f++)
        {
         if(PFieldIsToggle(f) || sparam != P_PFX "e_" + PFieldName(f))
            continue;
         if(!PEditable())
           {
            Print("panel: locked - switch trading off and close any position first");
            PanelDraw();                       // snap the text back
            return true;
           }
         if(PFieldApply(f, ObjectGetString(0, sparam, OBJPROP_TEXT)))
           {
            PrintFormat("panel: %s = %s %s", PFieldLabel(f), PFieldText(f), PFieldUnit(f));
            PStoreSave();
           }
         PanelDraw();                          // redraw either way, so a rejected
         return true;                          // edit snaps back to the real value
        }
     }
   return false;
  }
