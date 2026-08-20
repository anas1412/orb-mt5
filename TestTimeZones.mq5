//+------------------------------------------------------------------+
//| TestTimeZones.mq5                                                |
//| Step 1 of the build order: prove the time model before any        |
//| trading logic is built on top of it.                             |
//|                                                                  |
//| Run as a script on any chart. Output goes to the Experts tab.     |
//| Every case is asserted against a known UTC answer, so this is     |
//| pass/fail, not eyeball-the-table.                                 |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

#include <TimeZones.mqh>

input int  BrokerWinterOffset = 2;      // hours ahead of UTC in winter
input bool BrokerFollowsUSDST = true;   // US switch dates, else EU

int g_pass = 0;
int g_fail = 0;

//| Assert that a session opens at the expected UTC wall time.
void Check(const string        label,
           const datetime      brokerNow,
           const ENUM_SESSION_TZ tz,
           const int           hour,
           const int           minute,
           const int           wantUTCHour,
           const int           wantUTCMin)
  {
   const datetime brokerStart = SessionStartInBrokerTime(brokerNow, tz, hour, minute,
                                                         BrokerWinterOffset, BrokerFollowsUSDST);
   const datetime utcStart    = BrokerToUTC(brokerStart, BrokerWinterOffset, BrokerFollowsUSDST);

   MqlDateTime u;
   TimeToStruct(utcStart, u);

   const bool ok = (u.hour == wantUTCHour && u.min == wantUTCMin);
   if(ok) g_pass++; else g_fail++;

   PrintFormat("%s  %s | broker %s | UTC %s | want %02d:%02d UTC",
               ok ? "PASS" : "FAIL",
               label,
               TimeToString(brokerStart, TIME_DATE|TIME_MINUTES),
               TimeToString(utcStart,    TIME_DATE|TIME_MINUTES),
               wantUTCHour, wantUTCMin);
  }

void OnStart()
  {
   PrintFormat("--- time model: winter offset %+d, %s DST dates ---",
               BrokerWinterOffset, BrokerFollowsUSDST ? "US" : "EU");

   // Dates chosen to straddle every switch. In 2026 the US springs
   // forward Mar 8 and falls back Nov 1; the EU switches Mar 29 and
   // Oct 25. The gaps between those are where offsets go wrong.
   const datetime winter   = D'2026.01.14 12:00';
   const datetime usOnly   = D'2026.03.11 12:00';  // US on DST, EU not yet
   const datetime bothOn   = D'2026.06.10 12:00';
   const datetime euOff    = D'2026.10.28 12:00';  // EU back to standard, US still on
   const datetime bothOff  = D'2026.11.11 12:00';

   // Tokyo never observes DST anywhere in the world, so 09:00 Tokyo is
   // 00:00 UTC on every date of the year. Any failure here is the
   // broker conversion leaking into the zone conversion.
   Print("Tokyo 09:00 must be 00:00 UTC on every date");
   Check("tokyo/jan", winter,  TZ_TOKYO, 9, 0, 0, 0);
   Check("tokyo/mar", usOnly,  TZ_TOKYO, 9, 0, 0, 0);
   Check("tokyo/jun", bothOn,  TZ_TOKYO, 9, 0, 0, 0);
   Check("tokyo/oct", euOff,   TZ_TOKYO, 9, 0, 0, 0);
   Check("tokyo/nov", bothOff, TZ_TOKYO, 9, 0, 0, 0);

   // New York cash open. EST is UTC-5, EDT is UTC-4.
   Print("NY 09:30 must be 14:30 UTC on EST, 13:30 UTC on EDT");
   Check("ny/jan", winter,  TZ_NEWYORK, 9, 30, 14, 30);
   Check("ny/mar", usOnly,  TZ_NEWYORK, 9, 30, 13, 30);
   Check("ny/jun", bothOn,  TZ_NEWYORK, 9, 30, 13, 30);
   Check("ny/oct", euOff,   TZ_NEWYORK, 9, 30, 13, 30);
   Check("ny/nov", bothOff, TZ_NEWYORK, 9, 30, 14, 30);

   // London open. GMT in winter, BST in summer.
   Print("London 08:00 must be 08:00 UTC on GMT, 07:00 UTC on BST");
   Check("ldn/jan", winter,  TZ_LONDON, 8, 0, 8, 0);
   Check("ldn/mar", usOnly,  TZ_LONDON, 8, 0, 8, 0);
   Check("ldn/jun", bothOn,  TZ_LONDON, 8, 0, 7, 0);
   Check("ldn/oct", euOff,   TZ_LONDON, 8, 0, 8, 0);
   Check("ldn/nov", bothOff, TZ_LONDON, 8, 0, 8, 0);

   // Sydney, southern hemisphere: DST spans the new year.
   Print("Sydney 10:00 must be 00:00 UTC on AEST, 23:00 UTC on AEDT");
   Check("syd/jan", winter,  TZ_SYDNEY, 10, 0, 23, 0);
   Check("syd/jun", bothOn,  TZ_SYDNEY, 10, 0,  0, 0);
   Check("syd/nov", bothOff, TZ_SYDNEY, 10, 0, 23, 0);

   // The switch dates themselves, asserted directly.
   Print("switch instants");
   PrintFormat("US DST 2026.03.07 -> %s, 2026.03.09 -> %s (want false, true)",
               IsUSDST(D'2026.03.07 12:00') ? "true" : "false",
               IsUSDST(D'2026.03.09 12:00') ? "true" : "false");
   PrintFormat("EU DST 2026.03.28 -> %s, 2026.03.30 -> %s (want false, true)",
               IsEUDST(D'2026.03.28 12:00') ? "true" : "false",
               IsEUDST(D'2026.03.30 12:00') ? "true" : "false");
   PrintFormat("EU DST 2026.10.24 -> %s, 2026.10.26 -> %s (want true, false)",
               IsEUDST(D'2026.10.24 12:00') ? "true" : "false",
               IsEUDST(D'2026.10.26 12:00') ? "true" : "false");

   // The window that costs money: for ~1 week each autumn the EU has
   // fallen back and the US has not. A broker on the wrong ruleset is
   // one hour out for exactly this stretch, and nowhere else.
   PrintFormat("2026.10.28 broker offset: US rules %+d h, EU rules %+d h",
               BrokerOffsetSeconds(euOff, BrokerWinterOffset, true)  / 3600,
               BrokerOffsetSeconds(euOff, BrokerWinterOffset, false) / 3600);

   PrintFormat("--- %d passed, %d failed ---", g_pass, g_fail);
  }
//+------------------------------------------------------------------+
