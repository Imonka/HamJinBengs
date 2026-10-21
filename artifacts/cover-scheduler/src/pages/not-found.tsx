import { Link } from "wouter";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center rise">
      <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-primary">Error 404</div>
      <h1 className="font-display text-5xl font-extrabold mt-2">This shift does not exist.</h1>
      <p className="text-muted-foreground mt-3 max-w-sm">The page may have moved, or the link was mistyped. The roster is still where you left it.</p>
      <Link href="/" className="mt-6 inline-flex items-center h-10 px-4 rounded-md bg-primary text-primary-foreground font-medium" data-testid="link-home">Back to the desk</Link>
    </div>
  );
}
