// Dubai Property Risk site: links from config.js, the lazy Power BI embed and its fallback.
// No framework. Without JavaScript the page still works: the screenshots and findings show
// instead of the live report (styles.css: .js .fallback).
(function () {
  "use strict";
  var cfg = window.SITE_CONFIG || {};

  // Links that live in config.js. An empty value keeps the in-page default (e.g. #story).
  document.querySelectorAll("[data-config-href]").forEach(function (a) {
    var url = cfg[a.getAttribute("data-config-href")];
    if (url) {
      a.href = url;
      a.hidden = false;
    }
  });

  // Footer year.
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  // Larger view of a chart or report screenshot: a native <dialog> (Esc closes it, focus
  // stays inside and returns to the link). Without JavaScript the link opens the image.
  var zoomLinks = document.querySelectorAll("a.zoomable");
  if (zoomLinks.length && typeof HTMLDialogElement === "function") {
    var viewer = document.createElement("dialog");
    viewer.className = "viewer";
    viewer.setAttribute("aria-label", "Enlarged image");
    viewer.innerHTML =
      '<div class="viewer-bar"><p></p><button type="button" class="viewer-close">Close</button></div>' +
      '<div class="viewer-body"><img alt=""></div>';
    document.body.appendChild(viewer);
    var vImg = viewer.querySelector("img");
    var vCaption = viewer.querySelector(".viewer-bar p");
    var opener = null;
    viewer.querySelector(".viewer-close").addEventListener("click", function () { viewer.close(); });
    viewer.addEventListener("click", function (e) { if (e.target === viewer) viewer.close(); });
    viewer.addEventListener("close", function () {
      vImg.removeAttribute("src");
      if (opener) opener.focus();
    });
    zoomLinks.forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // new tab still works
        e.preventDefault();
        var thumb = a.querySelector("img");
        var fig = a.closest("figure");
        var cap = fig && fig.querySelector("figcaption");
        vImg.src = a.href;
        vImg.alt = thumb ? thumb.alt : "";
        vCaption.textContent = cap ? cap.textContent : "Press Esc or Close to return";
        opener = a;
        viewer.showModal();
      });
    });
  }

  var frame = document.getElementById("report-frame");
  var poster = document.getElementById("report-poster");
  var fallback = document.getElementById("report-fallback");
  var status = document.getElementById("report-status");
  var openLink = document.getElementById("report-open");
  if (!frame || !fallback) return;

  function showFallback() {
    frame.classList.add("is-failed");
    fallback.classList.add("is-shown");
    openLink.hidden = true;
    status.textContent = "";
  }

  // Publish to web stops working when the Power BI licence ends, and the iframe then loads
  // an error page (which still fires "load"), so the end date is the reliable switch.
  // Dubai time, end of the day.
  var expired = cfg.embedExpires && Date.now() > Date.parse(cfg.embedExpires + "T23:59:59+04:00");
  if (!cfg.embedUrl || expired) {
    showFallback();
    return;
  }

  openLink.href = cfg.embedUrl;
  openLink.hidden = false;

  var started = false;
  function load() {
    if (started) return;
    started = true;
    status.textContent = "Loading the report. It can take a few seconds.";
    var iframe = document.createElement("iframe");
    iframe.title = "Dubai Property and Mortgage Risk Analytics, Power BI report";
    iframe.src = cfg.embedUrl;
    iframe.allowFullscreen = true;
    var loaded = false;
    var timer = setTimeout(function () {
      if (!loaded) {
        iframe.remove();
        showFallback();
      }
    }, (cfg.embedTimeoutSeconds || 20) * 1000);
    iframe.addEventListener("load", function () {
      loaded = true;
      clearTimeout(timer);
      if (poster) poster.remove();
      status.textContent = "";
    });
    frame.appendChild(iframe);
  }

  if (poster) poster.addEventListener("click", load);
  // Load when the frame comes near the screen, so the report doesn't slow the first view.
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) {
          io.disconnect();
          load();
        }
      },
      { rootMargin: "200px" }
    );
    io.observe(frame);
  }
})();
