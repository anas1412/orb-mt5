//+------------------------------------------------------------------+
//| DumpD1.mq5                                                       |
//| Research tool. Writes the daily candles the EA would see through  |
//| iOpen/iClose(PERIOD_D1) to CSV, so a "yesterday's candle" filter  |
//| can be tested on exactly the bars it would read live.            |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
input int InpDaysBack = 1100;

void OnStart()
  {
   MqlRates r[];
   int got = 0, stable = 0;
   datetime to = TimeCurrent(), from = to - (datetime)InpDaysBack * 86400;
   for(int i = 0; i < 60; i++)              // CopyRates both reads and requests
     {
      int n = CopyRates(_Symbol, PERIOD_D1, from, to, r);
      if(n > 0 && n == got && ++stable >= 3) break;
      if(n > 0) got = n; else stable = 0;
      Sleep(1000);
     }
   int h = FileOpen(StringFormat("d1_%s.csv", _Symbol), FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   FileWrite(h, "day", "open", "high", "low", "close", "ticks");
   for(int i = 0; i < got; i++)
      FileWrite(h, TimeToString(r[i].time, TIME_DATE), DoubleToString(r[i].open, _Digits),
                DoubleToString(r[i].high, _Digits), DoubleToString(r[i].low, _Digits),
                DoubleToString(r[i].close, _Digits), (int)r[i].tick_volume);
   FileClose(h);
   PrintFormat("D1DUMP %d days", got);
   TerminalClose(0);
  }
