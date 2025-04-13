from flask import render_template, request
from services.rag_service import RAGService

def chat():
    """Handle chat functionality using RAG for question answering"""
    response = None
    user_input = None
    
    if request.method == 'POST':
        user_input = request.form['user_input']
        
        # Get RAG service and query
        rag_service = RAGService.get_instance()
        response = rag_service.query(user_input)
    
    return render_template('chat.html', response=response, user_input=user_input)