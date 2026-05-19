import { createDefine } from "fresh";

// Defines the state across the logger. Currently empty due to no middleware whatever that is.
export interface State {}

export const define = createDefine<State>();
