const GA_MEASUREMENT_ID = "G-XTFN4J69PT";

export const trackEvent = (
  eventName: string,
  params?: Record<string, unknown>
): void => {
  if (typeof window !== "undefined" && typeof window.gtag === "function") {
    window.gtag("event", eventName, params);
  }
};
