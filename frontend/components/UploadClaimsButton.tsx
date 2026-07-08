"use client";

import { useState } from "react";
import { UploadCloud } from "lucide-react";
import UploadClaimsModal from "./UploadClaimsModal";

export default function UploadClaimsButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="btn-toon inline-flex items-center gap-1.5 bg-cotiviti-teal px-4 py-2 text-sm font-bold text-white"
      >
        <UploadCloud size={16} strokeWidth={3} />
        Upload Claims
      </button>
      {open && <UploadClaimsModal onClose={() => setOpen(false)} />}
    </>
  );
}
