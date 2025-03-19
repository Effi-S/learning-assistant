from typing import Optional

import streamlit as st


def _inner(msg=None):
    if msg:
        st.write(msg)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes"):
            st.session_state.confirmation = True
            st.rerun()
    with col2:
        if st.button("No"):
            st.session_state.confirmation = False
            st.rerun()


def confirm_popup(title: str = "Confirmation", msg: str = None) -> Optional[bool]:
    if "confirmation" not in st.session_state:
        st.session_state.confirmation = None
    if st.session_state.confirmation is None:
        st.dialog(title)(_inner)(msg=msg)
        return None
    ret = st.session_state.confirmation
    st.session_state.confirmation = None
    return ret
