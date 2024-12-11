import streamlit as st

def run_code(code):
    import io
    import sys
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        exec(code, globals(), locals())
    except Exception as e:
        return str(e)
    finally:
        sys.stdout = sys.__stdout__
    return buffer.getvalue()

# Exercise page logic
if st.session_state.page == 'exercise':
    st.title("One-Sided ANOVA Exercise")

    st.write("### Instructions:")
    st.write("Write your code below to perform One-Sided ANOVA.")

    # Create a text area for code input
    code = st.text_area("Python Code", height=300)

    # Execute the code when the button is clicked
    if st.button("Run Code"):
        output = run_code(code)
        st.write("### Output:")
        st.code(output)

    # Display sample data for reference
    st.write("### Sample Data")
    import pandas as pd
    sample_data = pd.DataFrame({
        "Group": ["A", "A", "A", "B", "B", "B"],
        "Value": [1.2, 1.5, 1.3, 2.5, 2.7, 2.8]
    })
    st.write(sample_data)

    # Button to return to the main page
    if st.button('Back to Main Page'):
        st.session_state.page = 'main'
        st.experimental_rerun()
