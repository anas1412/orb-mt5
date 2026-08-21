//+------------------------------------------------------------------+
//| DumpRange.mq5                                                    |
//| Research tool. Writes M1 bars for a date range to Common\Files.   |
//|                                                                  |
//| Exists because the Strategy Tester refuses to test the current    |
//| calendar day, so BarDump cannot reach today's session. Run this   |
//| as a script on any chart and it reads straight from history.      |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input datetime InpFrom     = D'2026.08.21 00:00';   // from (broker time)
input datetime InpTo       = D'2026.08.22 00:00';   // to (broker time)
input int      InpFromHour = 1;                     // first broker hour to keep
input int      InpToHour   = 18;                    // last broker hour to keep

void OnStart()
  {
   MqlRates r[];
   const int n = CopyRates(_Symbol, PERIOD_M1, InpFrom, InpTo, r);
   if(n <= 0)
     {
      PrintFormat("no M1 bars between %s and %s — error %d",
                  TimeToString(InpFrom), TimeToString(InpTo), GetLastError());
      return;
     }

   const string name = StringFormat("bars_%s_extra.csv", _Symbol);
   const int h = FileOpen(name, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("cannot open %s: %d", name, GetLastError());
      return;
     }
   FileWrite(h, "time", "open", "high", "low", "close", "ticks", "volume");

   int kept = 0;
   for(int i = 0; i < n; i++)
     {
      MqlDateTime dt;
      TimeToStruct(r[i].time, dt);
      if(dt.hour < InpFromHour || dt.hour > InpToHour)
         continue;
      FileWrite(h,
                TimeToString(r[i].time, TIME_DATE|TIME_MINUTES),
                DoubleToString(r[i].open,  _Digits),
                DoubleToString(r[i].high,  _Digits),
                DoubleToString(r[i].low,   _Digits),
                DoubleToString(r[i].close, _Digits),
                IntegerToString(r[i].tick_volume),
                IntegerToString(r[i].real_volume));
      kept++;
     }
   FileClose(h);
   PrintFormat("wrote %d of %d bars to Common\\Files\\%s", kept, n, name);
  }
//+------------------------------------------------------------------+
