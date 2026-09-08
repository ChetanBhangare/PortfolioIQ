"use client";
import {Chart} from "./Plot";
import {REGIME_COLORS,REGIME_LABELS} from "@/lib/constants";
import type {RegimeHistoryPoint,RegimeName,RegimePerformance} from "@/lib/types";

const ORDER:RegimeName[]=["bull_low_vol","bull_high_vol","bear_low_vol","bear_high_vol"];

export function RegimeTimeline({rows}:{rows:RegimeHistoryPoint[]}){return <Chart ariaLabel="Historical market regime timeline" height={390} data={ORDER.map(regime=>{const points=rows.filter(row=>row.regime===regime);return {type:"scatter",mode:"markers",name:REGIME_LABELS[regime],x:points.map(row=>row.date),y:points.map(()=>REGIME_LABELS[regime]),marker:{color:REGIME_COLORS[regime],size:7},customdata:points.map(row=>[row.rolling_trend,row.realized_volatility]),hovertemplate:"%{x}<br>%{y}<br>Trend %{customdata[0]:.2%}<br>Volatility %{customdata[1]:.2%}<extra></extra>"};})} layout={{xaxis:{title:{text:"Date"}},yaxis:{categoryorder:"array",categoryarray:ORDER.map(regime=>REGIME_LABELS[regime])},legend:{orientation:"h",y:1.18}}}/>}

export function RegimeReturnChart({rows}:{rows:RegimePerformance[]}){return <Chart ariaLabel="Annualized portfolio return by market regime" data={[{type:"bar",x:rows.map(row=>REGIME_LABELS[row.regime]),y:rows.map(row=>row.annualized_return),marker:{color:rows.map(row=>REGIME_COLORS[row.regime])},hovertemplate:"%{x}<br>%{y:.2%}<extra></extra>"}]} layout={{yaxis:{title:{text:"Annualized Return"},tickformat:".0%"},showlegend:false}}/>}

export function RegimeVolatilityChart({rows}:{rows:RegimePerformance[]}){return <Chart ariaLabel="Annualized portfolio volatility by market regime" data={[{type:"bar",x:rows.map(row=>REGIME_LABELS[row.regime]),y:rows.map(row=>row.annualized_volatility),marker:{color:rows.map(row=>REGIME_COLORS[row.regime])},hovertemplate:"%{x}<br>%{y:.2%}<extra></extra>"}]} layout={{yaxis:{title:{text:"Annualized Volatility"},tickformat:".0%"},showlegend:false}}/>}
