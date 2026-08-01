import "./styles.css";
export const metadata = { title: "Relay AI Support", description: "Intent-routed, grounded customer support" };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
