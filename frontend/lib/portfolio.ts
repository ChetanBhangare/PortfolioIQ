import {DEFAULT_PORTFOLIO} from "./constants";
import type {PortfolioInput} from "./types";

export function normalizePortfolio(value:unknown):PortfolioInput{
  const candidate=value&&typeof value==="object"?value as Partial<PortfolioInput>:{};
  const portfolioName=typeof candidate.portfolio_name==="string"?candidate.portfolio_name.trim():"";
  return {
    ...DEFAULT_PORTFOLIO,
    ...candidate,
    portfolio_name:portfolioName||DEFAULT_PORTFOLIO.portfolio_name,
  };
}
