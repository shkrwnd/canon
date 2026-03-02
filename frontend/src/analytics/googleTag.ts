const GA_MEASUREMENT_ID = "G-XTFN4J69PT";

export function initGoogleTag() {
  // Only run GA in production builds
  if (typeof window === "undefined" || process.env.NODE_ENV !== "production") {
    return;
  }

  // Avoid double initialization
  if ((window as any).gtagInitialized) {
    return;
  }

  // Load gtag script
  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(script);

  // Initialize gtag
  (window as any).dataLayer = (window as any).dataLayer || [];
  function gtag(...args: any[]) {
    (window as any).dataLayer.push(args);
  }
  (window as any).gtag = gtag;
  (window as any).gtagInitialized = true;

  gtag("js", new Date());
  gtag("config", GA_MEASUREMENT_ID);
}

