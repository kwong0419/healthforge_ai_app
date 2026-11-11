import json

import streamlit as st
import streamlit.components.v1 as components

# Room for Streamlit's top bar, so the scrolled-to element isn't hidden under it.
_TOP_OFFSET_PX = 70

_SCROLL_SCRIPT = """
<script>
  // Run %(nonce)s: a new number each time, so the browser runs this again.
  (function () {
    var tries = 0;
    function scroll() {
      try {
        var el = window.parent.document.querySelector(%(selector)s);
        if (!el) {
          if (tries++ < 20) setTimeout(scroll, 100);
          return;
        }
        el.style.scrollMarginTop = "%(offset)dpx";
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (e) {
        // Scrolling is a nicety; never break the page over it.
      }
    }
    setTimeout(scroll, 150);
  })();
</script>
"""


def scroll_to(container_key: str) -> None:
    """
    Scrolls the page to the st.container with this key. Used after an action near the
    bottom of the page (e.g. saving an edit on a phone) so its message is in view.
    """
    nonce = st.session_state.get("_scroll_nonce", 0) + 1
    st.session_state._scroll_nonce = nonce
    selector = json.dumps(f".st-key-{container_key}")
    components.html(
        _SCROLL_SCRIPT % {"nonce": nonce, "selector": selector, "offset": _TOP_OFFSET_PX},
        height=0,
    )
