---
title: "Fresh Local Harvest"
description: "Up-to-date info on farmers markets and seasonal produce."
---
**Fresh Local Harvest** helps you find farmers markets and fresh produce—fast.  
This is the public site for the project. Explore the **Blog** for updates, and use **Map** to launch the interactive view (dev URL for now).
<hr />

<div id="api-status" style="font:14px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; margin-top:1rem;">
  <strong>API:</strong> <span id="api-status-text">checking…</span>
</div>

<script>
  // why: avoid breaking static export; run only when served from localhost (true dev)
  (function () {
    var isDevHost = (location.hostname === 'localhost' || location.hostname === '127.0.0.1');
    if (!isDevHost) {
      // Production or preview: keep UI but mark as inactive
      var t = document.getElementById('api-status-text');
      if (t) t.textContent = 'inactive (dev only)';
      return;
    }

    var t = document.getElementById('api-status-text');
    var controller = new AbortController();
    var timeout = setTimeout(function(){ controller.abort(); }, 3000);

    fetch('http://127.0.0.1:8001/health', { signal: controller.signal })
      .then(function(res){ clearTimeout(timeout); return res.ok ? res.json() : Promise.reject(new Error('HTTP '+res.status)); })
      .then(function(json){
        if (t) t.textContent = 'OK';
      })
      .catch(function(err){
        if (t) t.textContent = 'unreachable (start API on :8001)';
      });
  })();
</script>
