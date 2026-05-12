"use client";

import { useState, useCallback, useEffect } from "react";

import { cn } from "@/lib/utils";

interface ImgWithFallbackProps
  extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, "onError"> {
  sources: string[];
  fallbackElement?: React.ReactNode;
}

/**
 * Image component that cycles through a list of URL candidates on error.
 * When all sources fail, shows an optional fallback element or nothing.
 */
export function ImgWithFallback({
  sources,
  fallbackElement,
  className,
  alt,
  ...props
}: ImgWithFallbackProps) {
  const [index, setIndex] = useState(0);
  const [allFailed, setAllFailed] = useState(false);

  // Reset state when sources change (e.g. list virtualization reuse)
  const sourcesKey = sources.join(",");
  useEffect(() => {
    setIndex(0);
    setAllFailed(false);
     
  }, [sourcesKey]);

  const handleError = useCallback(() => {
    if (index + 1 < sources.length) {
      setIndex((prev) => prev + 1);
    } else {
      setAllFailed(true);
    }
  }, [index, sources.length]);

  if (allFailed || sources.length === 0) {
    return <>{fallbackElement}</> ;
  }

  return (
    <img
      src={sources[index]}
      alt={alt ?? ""}
      className={cn("object-cover", className)}
      onError={handleError}
      {...props}
    />
  );
}
