"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ChatRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[50vh] text-slate-400 text-xs">
      Đang chuyển tiếp về phòng Chat chính...
    </div>
  );
}
