import {PageHeader} from "@/components/common/PageHeader";import {PortfolioEditor} from "@/components/portfolio/PortfolioEditor";
export default function PortfolioPage(){return <><PageHeader eyebrow="PORTFOLIO CONFIGURATION" title="Portfolio Builder" description="Define the allocation, benchmark, analysis period, and risk-free rate used by every analytics module."/><PortfolioEditor/></>}
