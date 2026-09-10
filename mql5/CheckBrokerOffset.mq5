//+------------------------------------------------------------------+
//| CheckBrokerOffset.mq5                                            |
//| Diagnostic. Settles the two broker inputs the EA needs:          |
//|   BrokerWinterOffset  — from the live clock difference           |
//|   BrokerFollowsUSDST  — from where the weekly open moves         |
//|                                                                  |
//| This is the one file allowed to read the host clock. It is a     |
//| measuring tool, never compiled into the EA.                      |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string   InpSymbol = "EURUSD";
input datetime InpFrom   = D'2025.10.06 00:00';  // spans the EU switch (Oct 26)
input datetime InpTo     = D'2025.11.24 00:00';  // ...and the US switch (Nov 2)

void OnStart()
  {
   //--- current offset, straight from the clocks
   const datetime srv = TimeTradeServer();
   const datetime utc = TimeGMT();
   PrintFormat("server %s | UTC %s | offset %+d h",
               TimeToString(srv, TIME_DATE|TIME_MINUTES),
               TimeToString(utc, TIME_DATE|TIME_MINUTES),
               (int)MathRound((double)(srv - utc) / 3600.0));

   //--- weekly opens across both switch weekends
   //
   // The week opens at 17:00 New York, which is 21:00 UTC on EDT and
   // 22:00 UTC on EST. So in broker time:
   //
   //   broker follows US dates -> offset and the UTC open move on the
   //     same weekend, and the weekly open stays at one broker hour
   //     all year
   //   broker follows EU dates -> they move on different weekends, so
   //     the weekly open shifts an hour at the end of October and back
   //     at the start of November
   //
   // Read the column below. Constant means US, shifting means EU.
   MqlRates r[];
   const int n = CopyRates(InpSymbol, PERIOD_M1, InpFrom, InpTo, r);
   if(n <= 0)
     {
      PrintFormat("no M1 history for %s in that range — download it first "
                  "(Tools > Options > Charts, then open an M1 chart and page back)",
                  InpSymbol);
      return;
     }
   PrintFormat("%d M1 bars, %s to %s",
               n,
               TimeToString(r[0].time,   TIME_DATE|TIME_MINUTES),
               TimeToString(r[n-1].time, TIME_DATE|TIME_MINUTES));

   Print("weekly opens, broker time:");
   for(int i = 1; i < n; i++)
      if(r[i].time - r[i-1].time >= 12 * 3600)
         PrintFormat("  %s   (previous week closed %s)",
                     TimeToString(r[i].time,   TIME_DATE|TIME_MINUTES),
                     TimeToString(r[i-1].time, TIME_DATE|TIME_MINUTES));
  }
//+------------------------------------------------------------------+
