exports.handler = async (event) => {
  const BACKEND_URL = process.env.BACKEND_URL || "https://kalpana-4x49.onrender.com";

  const backendBase = BACKEND_URL.replace(/\/$/, "");
  const proxiedPath = (event.path || "").replace(/^\/\.netlify\/functions\/proxy/, "") || "/";
  const queryString = event.rawQuery ? `?${event.rawQuery}` : "";
  const targetUrl = `${backendBase}${proxiedPath}${queryString}`;

  const headers = { ...(event.headers || {}) };
  delete headers.host;
  delete headers["content-length"];

  const body = event.body
    ? event.isBase64Encoded
      ? Buffer.from(event.body, "base64")
      : event.body
    : undefined;

  try {
    const response = await fetch(targetUrl, {
      method: event.httpMethod,
      headers,
      body,
      redirect: "manual",
    });

    const contentType = response.headers.get("content-type") || "";
    const isText =
      contentType.startsWith("text/") ||
      contentType.includes("json") ||
      contentType.includes("javascript") ||
      contentType.includes("xml") ||
      contentType.includes("x-www-form-urlencoded");

    if (isText) {
      const textBody = await response.text();
      return {
        statusCode: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        body: textBody,
      };
    }

    const binary = Buffer.from(await response.arrayBuffer());
    return {
      statusCode: response.status,
      headers: Object.fromEntries(response.headers.entries()),
      body: binary.toString("base64"),
      isBase64Encoded: true,
    };
  } catch (error) {
    return {
      statusCode: 502,
      body: `Proxy error: ${error.message}`,
    };
  }
};
