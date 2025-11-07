# def search_books_information(namespace: str, query: str):
#     vector_store = VectorStoreManager.get_vector_store(namespace)
#     llm = LLMManager.get_llm(model="gemini-2.5-flash")
#     retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
#     qa_chain = ChainManager.get_qa_chain(llm, chain_type="stuff")
#     from langchain.chains import RetrievalQA
#
#     qa = RetrievalQA.from_chain_type(
#         llm=llm,
#         chain_type="stuff",
#         retriever=retriever,
#         return_source_documents=True,
#     )
#
#     result = qa.run(query)
#     return result