"use client";
import {createContext,useCallback,useContext,useEffect,useMemo,useState} from "react";
import {analyzePortfolio,analyzeRisk,optimizePortfolio} from "@/lib/api";
import {DEFAULT_PORTFOLIO} from "@/lib/constants";
import type {AnalysisBundle,PortfolioInput} from "@/lib/types";
type Status="idle"|"loading"|"success"|"error";
type ContextValue={portfolio:PortfolioInput;setPortfolio:(value:PortfolioInput)=>void;analysis:AnalysisBundle|null;status:Status;error:string|null;runAnalysis:()=>Promise<boolean>;runCustomShock:(shocks:Record<string,number>)=>Promise<void>;reset:()=>void};
const Context=createContext<ContextValue|null>(null);const STORAGE_KEY="portfolioiq:portfolio:v1";
export function PortfolioProvider({children}:{children:React.ReactNode}){const [portfolio,setPortfolioState]=useState(DEFAULT_PORTFOLIO);const [analysis,setAnalysis]=useState<AnalysisBundle|null>(null);const [status,setStatus]=useState<Status>("idle");const [error,setError]=useState<string|null>(null);
useEffect(()=>{try{const stored=localStorage.getItem(STORAGE_KEY);if(stored){const parsed=JSON.parse(stored) as {version:number;portfolio:PortfolioInput};if(parsed.version===1)setPortfolioState(parsed.portfolio)}}catch{}},[]);
const setPortfolio=useCallback((value:PortfolioInput)=>{setPortfolioState(value);localStorage.setItem(STORAGE_KEY,JSON.stringify({version:1,portfolio:value}))},[]);
const runAnalysis=useCallback(async()=>{setStatus("loading");setError(null);try{const [performance,risk,optimization]=await Promise.all([analyzePortfolio(portfolio),analyzeRisk(portfolio),optimizePortfolio(portfolio)]);setAnalysis({portfolio:performance,risk,optimization});setStatus("success");return true}catch(value){setStatus("error");setError(value instanceof Error?value.message:"Unexpected analytics error.");return false}},[portfolio]);
const runCustomShock=useCallback(async(shocks:Record<string,number>)=>{setStatus("loading");setError(null);try{const optimization=await optimizePortfolio(portfolio,shocks);setAnalysis(current=>current?{...current,optimization}:current);setStatus("success")}catch(value){setStatus("error");setError(value instanceof Error?value.message:"Unexpected analytics error.")}},[portfolio]);
const reset=useCallback(()=>{setPortfolio(DEFAULT_PORTFOLIO);setAnalysis(null);setStatus("idle");setError(null)},[setPortfolio]);
const value=useMemo(()=>({portfolio,setPortfolio,analysis,status,error,runAnalysis,runCustomShock,reset}),[portfolio,setPortfolio,analysis,status,error,runAnalysis,runCustomShock,reset]);return <Context.Provider value={value}>{children}</Context.Provider>}
export function usePortfolio(){const value=useContext(Context);if(!value)throw new Error("usePortfolio must be used inside PortfolioProvider");return value}
