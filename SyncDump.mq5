//+------------------------------------------------------------------+
//| SyncDump.mq5                                                     |
//| Research tool, not a strategy.                                   |
//|                                                                  |
//| The Strategy Tester can only test over bars the terminal already  |
//| holds, and the terminal only downloads M1 history when a chart    |
//| asks for it. After a weekend that leaves the tester silently      |
//| clamping its date range to the last cached day, which looks like  |
//| "the backtest found no trades" rather than "the data is missing". |
//|                                                                  |
//| This runs on a LIVE chart, where CopyRates triggers the download, |
//| waits for the series to synchronise, then writes the recent bars  |
//| to CSV for merging into the research dataset.                    |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input int    InpDaysBack  = 30;            // how far back to fetch
input int    InpWaitSecs  = 90;            // give up after this long

void OnStart()
  {
   // Counted back from the server's clock, not written as a date: a fixed date
   // silently stops covering the gap as soon as it falls behind.
   datetime to   = TimeCurrent();
   datetime from = to - (datetime)InpDaysBack * 86400;
   MqlRates r[];
   int got = 0, stable = 0;

   // CopyRates on a live chart both reads and REQUESTS. The first calls
   // usually fail or come back short while the download is in flight, so poll
   // until the count stops growing rather than trusting a single call.
   for(int i = 0; i < InpWaitSecs; i++)
     {
      int n = CopyRates(_Symbol, PERIOD_M1, from, to, r);
      if(n > 0 && n == got)
        {
         if(++stable >= 3)
            break;               // three quiet seconds means the fetch is done
        }
      else
         stable = 0;
      if(n > 0)
         got = n;
      Sleep(1000);
     }

   if(got <= 0)
     {
      Print("no bars available after waiting, terminal may be offline");
      return;
     }

   string name = StringFormat("sync_%s.csv", _Symbol);
   int h = FileOpen(name, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|
                          FILE_SHARE_READ|FILE_SHARE_WRITE, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("cannot open %s: %d", name, GetLastError());
      return;
     }
   FileWrite(h, "time", "open", "high", "low", "close", "ticks", "volume");
   for(int i = 0; i < got; i++)
      FileWrite(h,
                TimeToString(r[i].time, TIME_DATE|TIME_MINUTES),
                DoubleToString(r[i].open,  _Digits),
                DoubleToString(r[i].high,  _Digits),
                DoubleToString(r[i].low,   _Digits),
                DoubleToString(r[i].close, _Digits),
                (int)r[i].tick_volume,
                (int)r[i].real_volume);
   FileClose(h);

   PrintFormat("SYNCDUMP %d bars, %s .. %s -> %s", got,
               TimeToString(r[0].time,       TIME_DATE|TIME_MINUTES),
               TimeToString(r[got-1].time,   TIME_DATE|TIME_MINUTES), name);
   TerminalClose(0);
  }
