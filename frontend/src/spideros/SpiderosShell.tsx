import type { ReactNode } from "react";
import { Navbar } from "./Navbar";
import "./shell.css";

interface Props {
  children: ReactNode;
}

export function SpiderosShell({ children }: Props) {
  return (
    <>
      <Navbar />
      <div className="spideros-shell__content">{children}</div>
    </>
  );
}
