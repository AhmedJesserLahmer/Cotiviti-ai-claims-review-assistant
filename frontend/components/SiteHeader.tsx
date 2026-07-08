import Link from "next/link";
import { Stethoscope, Radar } from "lucide-react";
import CotivitiLogo from "./CotivitiLogo";

export default function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b-[3px] border-cotiviti-ink bg-cotiviti-cream/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="transition-transform hover:-rotate-2">
          <CotivitiLogo />
        </Link>
        <div className="flex items-center gap-3">
          <Link
            href="/providers"
            className="chip-toon hidden items-center gap-1.5 bg-cotiviti-teal px-3 py-1 text-sm font-extrabold text-white transition-transform hover:-translate-y-0.5 sm:flex"
          >
            <Radar size={15} strokeWidth={3} />
            Providers
          </Link>
          <span className="hidden items-center gap-2 rounded-full border-[2.5px] border-cotiviti-ink bg-cotiviti-gold px-3 py-1 text-sm font-extrabold text-cotiviti-ink shadow-[2px_2px_0_0_var(--color-cotiviti-ink)] md:flex">
            <Stethoscope size={16} strokeWidth={3} />
            AI Claims Review Assistant
          </span>
        </div>
      </div>
    </header>
  );
}
