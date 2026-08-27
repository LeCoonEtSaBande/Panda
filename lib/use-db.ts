"use client";

import { useEffect, useState } from "react";
import { getCachedDb, hydrateDb, subscribeStore } from "@/lib/store";
import type { Db } from "@/lib/types";

export function useDb(): Db {
  const [db, setDb] = useState<Db>(getCachedDb);
  useEffect(() => {
    void hydrateDb().then(setDb);
    return subscribeStore(() => setDb(getCachedDb()));
  }, []);
  return db;
}
