"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ChatRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[50vh] text-slate-500 text-xs font-medium">
      Đang chuyển tiếp về phòng Chat chính...
    </div>
  );
}
