const API_BASE=process.env.NEXT_PUBLIC_API_BASE_URL??"http://localhost:8000";
export async function getHealth(){const r=await fetch(`${API_BASE}/health`,{cache:"no-store"});if(!r.ok)throw new Error("backend unavailable");return r.json();}
