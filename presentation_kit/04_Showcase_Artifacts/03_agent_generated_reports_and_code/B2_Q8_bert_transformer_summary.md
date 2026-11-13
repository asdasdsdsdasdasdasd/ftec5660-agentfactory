# BERT (language model)

**Source:** https://en.wikipedia.org/wiki/BERT_%28language_model%29#1

**Task:** Use Google to search for and open Wikipedia, find the 'BERT (language model)' page (https://en.wikipedia.org/wiki/BERT_(language_model)). Extract its core definition (what BERT stands for: Bidirectional Encoder Representations from Transformers, and its core description). Then summarize the main ideas of the Transformer architecture (self-attention, encoder-decoder, bidirectional context, pre-training/fine-tuning). Save the final results to a markdown file with: a title, the BERT core definition, and a summary of the Transformer architecture's main ideas.

## Core Definition

Bidirectional encoder representations from transformers (BERT) is a language model introduced in October 2018 by researchers at Google. It learns to represent text as a sequence of vectors using self-supervised learning and utilizes the encoder-only transformer architecture to dramatically improve the state of the art for large language models.

## Summary

BERT operates on an "encoder-only" transformer architecture, distinct from traditional encoder-decoder models. The architecture consists of four main modules: a Tokenizer (using WordPiece), an Embedding layer (combining token type, position, and segment embeddings), a stack of Transformer encoder blocks, and a Task head. The encoder blocks utilize self-attention mechanisms without causal masking, allowing the model to process input bidirectionally. This bidirectional context is a core feature, enabling BERT to understand relationships between words from both left and right contexts simultaneously, rather than sequentially.

The training methodology is defined by two primary pre-training tasks. First, Masked Language Modeling (MLM) involves randomly masking 15% of tokens, with 80% replaced by a [MASK] token, 10% by a random word, and 10% left unchanged, to predict the original token based on context. Second, Next Sentence Prediction (NSP) trains the model to determine if two sentences appear sequentially in the corpus, helping it understand inter-sentence relationships.

For downstream applications, BERT employs a fine-tuning approach. The pre-trained task head is removed and replaced with a newly initialized module suited for specific tasks, such as question answering or sentiment classification. The latent vector representations from the encoder are fed directly into this new module, allowing for sample-efficient transfer learning. Originally released in BERTBASE (110 million parameters) and BERTLARGE (340 million parameters), the model was trained on the Toronto BookCorpus and English Wikipedia.

## Key Points

- BERT stands for Bidirectional encoder representations from transformers and uses an encoder-only architecture.
- The model learns bidirectional context through self-attention mechanisms without causal masking.
- Pre-training relies on Masked Language Modeling (MLM) and Next Sentence Prediction (NSP).
- Fine-tuning involves replacing the task head with a task-specific module for downstream NLP tasks.
- The embedding layer combines token type, absolute position, and segment type embeddings.
- BERT dramatically improved state-of-the-art performance in natural language processing tasks.
