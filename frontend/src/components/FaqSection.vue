<template>
    <section class="faq-section py-5 px-3">
      <div class="container">
        <h2 class="text-center display-5 fw-bold mb-3">Frequently asked questions</h2>
        <p class="text-center text-muted mb-5">
          Easy answers to the product questions we get most often.
        </p>
  
        <div class="accordion accordion-flush" id="faqAccordion">
          <div
            class="accordion-item"
            v-for="(faq, index) in faqs"
            :key="index"
          >
            <h2 class="accordion-header" :id="`heading-${index}`">
              <button
                class="accordion-button collapsed"
                type="button"
                data-bs-toggle="collapse"
                :data-bs-target="`#collapse-${index}`"
                aria-expanded="false"
                :aria-controls="`collapse-${index}`"
              >
                {{ faq.question }}
              </button>
            </h2>
            <div
              :id="`collapse-${index}`"
              class="accordion-collapse collapse"
              :aria-labelledby="`heading-${index}`"
              data-bs-parent="#faqAccordion"
            >
              <div class="accordion-body">
                <span v-html="faq.answer"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA box below FAQ -->
<div class="contact-cta text-center mt-5 py-5 px-4 rounded">
  <div class="d-flex justify-content-center mb-3">
    <img
      src="/img/ai-1.jpg"
      alt="User 1"
      class="rounded-circle me-1"
      width="50"
      height="50"
    />
    <img
      src="/img/ai-2.jpg"
      alt="User 2"
      class="rounded-circle me-1"
    width="50"
      height="50"
    />
    <img
      src="/img/ai-3.jpg"
      alt="User 3"
      class="rounded-circle"
      width="50"
      height="50"
    />
  </div>

  <h3 class="h3 fw-semibold mb-2">Still have questions?</h3>
  <p class="h4 text-muted mb-4">Can’t find the answer you’re looking for? Just chat with our friendly team.</p>
  <button class="btn btn-brown">Get in touch</button>
</div>
  </template>
  
  <script setup>
const faqs = [
  {
    question: 'What are the benefits of using AIVA over ChatGPT?',
    answer: 'AIVA is specifically designed for interacting with complex documents like PDFs. It offers built-in features for search, summarization, and quick navigation that go beyond general-purpose chat tools.',
  },
  {
    question: 'Does AIVA Offer A Free Trial?',
    answer: 'Yes, all new users start with access to a free tier that includes essential features. You can explore the platform without any commitment before choosing to upgrade.',
  },
  {
    question: "Can I Modify My AIVA Subscription After I've Started Using It?",
    answer: 'Absolutely. You can upgrade, downgrade, or cancel your plan at any time directly from your account dashboard.',
  },
  {
    question: "What Is AIVA's Cancellation Policy?",
    answer: 'You can cancel your subscription at any point. Your plan will remain active until the end of the current billing period, after which you won’t be charged.',
  },
  {
    question: "Can Additional Information Be Included In AIVA's Invoice?",
    answer: 'Yes, you can add your company details, VAT ID, or billing address directly under "Account Settings > Billing". This helps ensure your invoices meet your accounting requirements.',
  },
  {
    question: 'How Does Billing Work For AIVA?',
    answer:
      'AIVA operates on a flexible monthly subscription model with different plans based on your needs. For full pricing information and billing options, see our pricing page.',
  },
];

</script>
  
<style scoped>
.container p{
  font-size: 1.8rem;
}

.accordion-button {
  padding-top: 1.2rem;
  padding-bottom: 1.2rem;
  font-size: 1.5rem;
  font-weight: 500;
}

.accordion-button:not(.collapsed) {
  background-color: rgb(179, 137, 110);
  color: rgb(255, 253, 253);
}

.accordion-button:not(.collapsed)::after {
  filter: brightness(0) invert(1);
}

.faq-section {
  background-color: rgb(253, 246, 243);
}

.accordion-button:focus {
  box-shadow: none;
}

.accordion-body {
  font-size: 1.5rem;
  color: rgb(68, 68, 68);
}

.contact-cta {
  background-color: rgb(248, 249, 250);
  border-radius: 1rem;
}

.contact-cta img {
  object-fit: cover;
  border: 0.125rem solid rgb(255, 255, 255); 
  box-shadow: 0 0 0 0.125rem rgb(255, 255, 255);
}

.btn-brown {
  background-color: rgb(179, 137, 110);
  color: rgb(255, 255, 255);
  font-weight: 600;
  border-radius: 0.375rem;
  transition: background-color 0.3s ease;
  padding: 0.8rem 1rem;
  font-size: 1.2rem;
}

.btn-brown:hover {
  background-color: rgb(133, 102, 82);
}

@media (max-width: 992px) {
  .container h2{
  font-size: 2rem;
  }

  .container p{
  font-size: 1.5rem;
  }

  .accordion-button {
    font-size: 0.8rem;
    padding-top: 0.8rem;
    padding-bottom: 0.8rem;
  }

  .accordion-body {
    font-size: 1rem;
  }

  .btn-brown {
    font-size: 1rem;
    padding: 0.4rem 0.8rem;
  }
}

@media (max-width: 768px) {
  .container h2{
  font-size: 1.75rem;
  }

  .container p{
  font-size: 1.2rem;
  }

  .accordion-button {
    font-size: 1rem;
    padding-top: 1rem;
    padding-bottom: 1rem;
  }

  .accordion-body {
    font-size: 1rem;
  }

  .btn-brown {
    font-size: 1.2rem;
    padding: 0.4rem 0.8rem;
  }

  p {
    font-size: 1.1rem;
  }
}
</style>
  