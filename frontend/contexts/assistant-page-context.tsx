"use client";
import { createContext, useContext } from "react";
import type { PageContext } from "@/lib/agent-types";

export const AssistantPageContext = createContext<PageContext>({ page: "single" });
export const useAssistantPageContext = () => useContext(AssistantPageContext);
