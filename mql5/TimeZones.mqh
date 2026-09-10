//+------------------------------------------------------------------+
//| TimeZones.mqh                                                    |
//| Broker time <-> UTC <-> session time.                            |
//|                                                                  |
//| Never reads the host clock. Everything derives from the datetime  |
//| the caller passes in, which comes from TimeCurrent() in live and  |
//| from the tester's simulated clock in a backtest. That is what     |
//| makes the results identical on Windows and on Wine.              |
//+------------------------------------------------------------------+
#property strict

enum ENUM_SESSION_TZ
  {
   TZ_UTC     = 0,
   TZ_LONDON  = 1,
   TZ_NEWYORK = 2,
   TZ_TOKYO   = 3,
   TZ_SYDNEY  = 4,
   TZ_BROKER  = 5
  };

//+------------------------------------------------------------------+
//| Calendar helpers                                                 |
//+------------------------------------------------------------------+
int DaysInMonth(const int year, const int month)
  {
   static int days[12] = {31,28,31,30,31,30,31,31,30,31,30,31};
   if(month == 2 && (year%4 == 0 && (year%100 != 0 || year%400 == 0)))
      return 29;
   return days[month-1];
  }

//| Midnight UTC of the nth `dow` in a month. nth = -1 means the last.
//| dow follows MqlDateTime.day_of_week: 0 = Sunday.
datetime NthDowOfMonth(const int year, const int month, const int dow, const int nth)
  {
   MqlDateTime dt;
   ZeroMemory(dt);
   dt.year = year;
   dt.mon  = month;
   dt.day  = 1;

   datetime first = StructToTime(dt);
   TimeToStruct(first, dt);
   const int firstDow = dt.day_of_week;

   int day;
   if(nth > 0)
     {
      day = 1 + ((dow - firstDow) + 7) % 7 + (nth - 1) * 7;
     }
   else
     {
      const int dim     = DaysInMonth(year, month);
      const int lastDow = (firstDow + dim - 1) % 7;
      day = dim - ((lastDow - dow) + 7) % 7;
     }

   ZeroMemory(dt);
   dt.year = year;
   dt.mon  = month;
   dt.day  = day;
   return StructToTime(dt);
  }

//+------------------------------------------------------------------+
//| DST rules. Hardcoded — MQL5 has no timezone database.            |
//| Switch instants are expressed in UTC.                            |
//+------------------------------------------------------------------+

//| US: 2nd Sun Mar 02:00 local (07:00 UTC) -> 1st Sun Nov 02:00 (06:00 UTC)
bool IsUSDST(const datetime utc)
  {
   MqlDateTime dt;
   TimeToStruct(utc, dt);
   const datetime start = NthDowOfMonth(dt.year, 3,  0,  2) + 7 * 3600;
   const datetime end   = NthDowOfMonth(dt.year, 11, 0,  1) + 6 * 3600;
   return (utc >= start && utc < end);
  }

//| EU: last Sun Mar 01:00 UTC -> last Sun Oct 01:00 UTC
bool IsEUDST(const datetime utc)
  {
   MqlDateTime dt;
   TimeToStruct(utc, dt);
   const datetime start = NthDowOfMonth(dt.year, 3,  0, -1) + 1 * 3600;
   const datetime end   = NthDowOfMonth(dt.year, 10, 0, -1) + 1 * 3600;
   return (utc >= start && utc < end);
  }

//| Australia, southern hemisphere: DST spans the new year.
//| 1st Sun Oct -> 1st Sun Apr, 02:00 local. Both fall inside the
//| weekend market gap, so the exact hour never affects a session.
bool IsAUDST(const datetime utc)
  {
   MqlDateTime dt;
   TimeToStruct(utc, dt);
   const datetime end   = NthDowOfMonth(dt.year, 4,  0, 1) + 16 * 3600;
   const datetime start = NthDowOfMonth(dt.year, 10, 0, 1) + 16 * 3600;
   return (utc < end || utc >= start);
  }

//+------------------------------------------------------------------+
//| Broker <-> UTC                                                   |
//+------------------------------------------------------------------+

//| Seconds the broker server sits ahead of UTC at this instant.
//|
//| The DST test needs UTC, but obtaining UTC needs the offset. We
//| break the loop with the winter offset, which is at most one hour
//| out. That only misreads the switch itself, in the small hours of a
//| Sunday, when no session is open. Do not "fix" it by feeding the
//| result back in — that trades a harmless error for an oscillation.
int BrokerOffsetSeconds(const datetime brokerTime,
                        const int      winterOffsetHours,
                        const bool     followsUSDST)
  {
   const datetime approxUTC = brokerTime - (datetime)(winterOffsetHours * 3600);
   const bool     dst       = followsUSDST ? IsUSDST(approxUTC) : IsEUDST(approxUTC);
   return (winterOffsetHours + (dst ? 1 : 0)) * 3600;
  }

datetime BrokerToUTC(const datetime brokerTime,
                     const int      winterOffsetHours,
                     const bool     followsUSDST)
  {
   return brokerTime - (datetime)BrokerOffsetSeconds(brokerTime, winterOffsetHours, followsUSDST);
  }

datetime UTCToBroker(const datetime utc,
                     const int      winterOffsetHours,
                     const bool     followsUSDST)
  {
   const bool dst = followsUSDST ? IsUSDST(utc) : IsEUDST(utc);
   return utc + (datetime)((winterOffsetHours + (dst ? 1 : 0)) * 3600);
  }

//+------------------------------------------------------------------+
//| Session zone <-> UTC                                             |
//+------------------------------------------------------------------+
int ZoneOffsetSeconds(const ENUM_SESSION_TZ tz,
                      const datetime        utc,
                      const int             winterOffsetHours,
                      const bool            followsUSDST)
  {
   switch(tz)
     {
      case TZ_UTC:     return 0;
      case TZ_LONDON:  return (IsEUDST(utc) ? 1 : 0) * 3600;
      case TZ_NEWYORK: return (IsUSDST(utc) ? -4 : -5) * 3600;
      case TZ_TOKYO:   return 9 * 3600;                        // never observes DST
      case TZ_SYDNEY:  return (IsAUDST(utc) ? 11 : 10) * 3600;
      case TZ_BROKER:  return (winterOffsetHours + ((followsUSDST ? IsUSDST(utc) : IsEUDST(utc)) ? 1 : 0)) * 3600;
     }
   return 0;
  }

//+------------------------------------------------------------------+
//| The one function the EA actually calls.                          |
//|                                                                  |
//| Given any instant in broker time, return the broker time at which |
//| that zone's session opens on the same zone-local calendar day.    |
//|                                                                  |
//| Resolved iteratively: the zone offset depends on the instant we   |
//| are trying to find. One refinement pass converges everywhere      |
//| except inside the switch hour itself.                            |
//+------------------------------------------------------------------+
datetime SessionStartInBrokerTime(const datetime        brokerNow,
                                  const ENUM_SESSION_TZ tz,
                                  const int             startHour,
                                  const int             startMinute,
                                  const int             winterOffsetHours,
                                  const bool            followsUSDST)
  {
   const datetime utcNow = BrokerToUTC(brokerNow, winterOffsetHours, followsUSDST);

   int zoneOff = ZoneOffsetSeconds(tz, utcNow, winterOffsetHours, followsUSDST);

   MqlDateTime z;
   TimeToStruct(utcNow + (datetime)zoneOff, z);
   z.hour = startHour;
   z.min  = startMinute;
   z.sec  = 0;

   const datetime zoneStart = StructToTime(z);

   datetime utcStart = zoneStart - (datetime)zoneOff;
   zoneOff  = ZoneOffsetSeconds(tz, utcStart, winterOffsetHours, followsUSDST);
   utcStart = zoneStart - (datetime)zoneOff;

   return UTCToBroker(utcStart, winterOffsetHours, followsUSDST);
  }
//+------------------------------------------------------------------+
