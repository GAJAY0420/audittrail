document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id === "timeline-body") {
        console.debug("Audit timeline updated", new Date().toISOString());
    }
});
