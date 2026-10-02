const quizAnswerHover = window.matchMedia("(hover: hover) and (pointer: fine)")

document$.subscribe(({ body }) => {
  body.querySelectorAll("details.quiz-answer").forEach((details) => {
    if (details.dataset.quizAnswerReady === "true") return

    const summary = details.querySelector(":scope > summary")
    if (!summary) return

    details.dataset.quizAnswerReady = "true"

    details.addEventListener("pointerenter", (event) => {
      if (!quizAnswerHover.matches || event.pointerType === "touch" || details.open) return

      details.dataset.quizHoverOpen = "true"
      details.open = true
    })

    details.addEventListener("pointerleave", () => {
      if (details.dataset.quizHoverOpen !== "true") return

      details.open = false
      delete details.dataset.quizHoverOpen
    })

    summary.addEventListener("click", (event) => {
      if (details.dataset.quizHoverOpen !== "true") return

      event.preventDefault()
      delete details.dataset.quizHoverOpen
      details.open = true
    })
  })
})
