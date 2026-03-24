import { useMemo } from "react";

export function Footer() {
  const year = useMemo(() => new Date().getFullYear(), []);
  return (
    <footer className="container-md mx-auto mt-32 flex flex-col items-center justify-center">
      <hr className="from-border/0 to-border/0 m-0 h-px w-full border-none bg-linear-to-r via-white/20" />
      <div className="text-muted-foreground container mb-8 flex flex-col items-center justify-center gap-4 py-8 text-xs">
        <div className="flex gap-4">
          <span>Privacy</span>
          <span>Terms</span>
          <a href="mailto:support@allo.example.com">Contact</a>
        </div>
        <p>&copy; {year} Allo</p>
      </div>
    </footer>
  );
}
