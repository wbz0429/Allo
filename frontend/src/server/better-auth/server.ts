import { cache } from "react";

import { getLocalDevSessionFromCookies } from "./local-dev";

export const getSession = cache(async () => getLocalDevSessionFromCookies());
