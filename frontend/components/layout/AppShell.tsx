import {Sidebar} from "./Sidebar";import {Header} from "./Header";
export function AppShell({children}:{children:React.ReactNode}){return <div className="app-shell"><Sidebar/><div className="workspace"><Header/><main className="content">{children}</main></div></div>}
