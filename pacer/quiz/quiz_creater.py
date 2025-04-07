from langchain.prompts import PromptTemplate
from langchain.schema import Document
from pydantic import BaseModel, Field, field_validator

from pacer.llms.llm_adapter import LLMSwitch
from pacer.tools import rag

quiz_prompt = PromptTemplate(
    input_variables=["text"],
    template=(
        "Generate a multiple-choice quiz with 10 questions. Each question should have 4 options, "
        "with the correct answer marked clearly."
        "Based on the following text:\n{text}\n\n"
    ),
)

quiz_append_prompt = PromptTemplate(
    input_variables=["text"],
    template=(
        "Add 10 new questions to the questions below."
        "Each question should have 4-6 options, "
        "with the correct answer marked clearly."
        "The Questions:\n{questions}\n\n"
        "Base questions on the following text:\n{text}\n\n"
    ),
)


class QuizQuestion(BaseModel):
    question: str
    answer: str
    options: list[str] = Field(default_factory=list)

    def model_post_init(self, *args, **kwargs):

        if (
            all(opt[1:2] in (")", ".") for opt in self.options)
            and len(self.answer) == 1
        ):
            # Edgecase example:
            # -------
            # QuizQuestion(question="What is the capital of France?",
            # answer="A",
            # options=["A) Paris", "B) London", "C) Berlin", "D) Madrid"])
            #
            # Converts to:
            # ---------
            # QuizQuestion(question="What is the capital of France?",
            #    answer="Paris",
            #    options=["Paris", "London", "Berlin", "Madrid"]
            # )
            # -1- Update answer
            for option in self.options:
                if option.startswith(self.answer):
                    self.answer = option[2:].strip()

            # -2- Update Options
            self.options = [opt[2:].strip() for opt in self.options]


class Quiz(BaseModel):
    questions: list[QuizQuestion]
    # answers: list[str] = Field(default_factory=list)


def create_quiz(documents: list[Document], llm=None) -> Quiz:
    llm = llm or LLMSwitch.get_current()
    # -1- Gather sources
    texts = [doc.page_content for doc in documents]
    combined_text = "\n".join(texts)

    print("Combined:", combined_text)
    # -2- structured chain

    chain = quiz_prompt | llm.with_structured_output(Quiz)

    return chain.invoke(dict(text=combined_text))


def add_questions(documents: list[Document], quiz: Quiz, llm=None) -> Quiz:
    llm = llm or LLMSwitch.get_current()
    # -1- Gather sources
    texts = [doc.page_content for doc in documents]
    combined_text = "\n".join(texts)

    # -2- structured chain
    chain = quiz_append_prompt | llm.with_structured_output(Quiz)
    questions_json = [q.model_dump_json(indent=2) for q in quiz.questions]
    res: Quiz = chain.invoke(dict(text=combined_text, questions=str(questions_json)))

    # -3- merge (just-in-case)
    res_questions = {q.question for q in res.questions}
    for q in quiz.questions:
        if q.question not in res_questions:
            res.questions.append(q)
    quiz.questions = res.questions
    return res
