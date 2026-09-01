const dash="—";
export const formatPercent=(v:number|null|undefined,digits=2)=>v==null||!Number.isFinite(v)?dash:new Intl.NumberFormat("en-US",{style:"percent",minimumFractionDigits:digits,maximumFractionDigits:digits}).format(v);
export const formatWeight=(v:number|null|undefined)=>formatPercent(v,1);
export const formatRatio=(v:number|null|undefined,digits=2)=>v==null||!Number.isFinite(v)?dash:v.toFixed(digits);
export const formatNumber=(v:number|null|undefined,digits=2)=>v==null||!Number.isFinite(v)?dash:new Intl.NumberFormat("en-US",{maximumFractionDigits:digits,minimumFractionDigits:digits}).format(v);
export const formatDate=(v:string|null|undefined)=>v?new Intl.DateTimeFormat("en-US",{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"}).format(new Date(v)):dash;
export const titleCase=(v:string)=>v.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
