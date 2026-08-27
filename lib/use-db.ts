"use client";

import { useEffect, useState } from "react";
import { getDb, subscribe, type Db } from "@/lib/local-db";

export function useDb(): Db {
  const [db, setDb] = useState<Db>({ tasks: [], contacts: [], grocery: [] });
  useEffect(() => {
    setDb(getDb());
    return subscribe(() => setDb(getDb()));
  }, []);
  return db;
}
