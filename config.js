// Site settings: the one place to update links (docs/07 §4). Read by main.js.
window.SITE_CONFIG = {
  // Power BI Publish to web link (docs/08, Publishing record). A test checks they match.
  embedUrl:
    "https://app.fabric.microsoft.com/view?r=eyJrIjoiYzgxYTFiNGEtNTQ1OC00YWExLTk2YTctY2E2MDMwNjQyNjY5IiwidCI6ImQ0M2RmOTBjLTEwYTctNDg5MC1hYjBjLWU5YWMwNDQ2NjRiNCJ9",
  // The Power BI licence behind the embed ends about this date. After it, the page shows
  // the screenshots instead of the live report. Move the date on if the licence is renewed.
  embedExpires: "2026-11-27",
  // Seconds to wait for the report before showing the screenshots instead.
  embedTimeoutSeconds: 20,
  repoUrl: "https://github.com/SafwanTisekar/dubai-property-analytics",
  githubProfileUrl: "https://github.com/SafwanTisekar",
  // Leave empty to hide the CV button; set to e.g. "/assets/cv.pdf" once the file is added.
  cvUrl: "",
  // A walkthrough video, if one is recorded later. Empty: the button jumps to the story.
  walkthroughUrl: "",
};
