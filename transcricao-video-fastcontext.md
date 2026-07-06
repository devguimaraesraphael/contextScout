# Transcript (translated): "46% Of Your Agent's Tokens Go To Waste (FastContext Fixes It)"

- **URL**: https://www.youtube.com/watch?v=GHc6edoG0RQ
- **Channel**: Hora de Codar
- **Original language**: Portuguese (Brazil). **Caption source**: auto-generated captions (pt), pulled via `yt-dlp`. This file is an English translation of that original transcript, done for this project's internal documentation.

## Summary (original video description)

FastContext is a Microsoft open-source project that attacks a problem almost
nobody notices, but that's costing you a lot: your AI agent spends a huge
chunk of its tokens just searching for code in the project, before it even
starts solving the task. FastContext's proposal is to separate these two
things, search and resolution, delegating repository exploration to a
specialized scout that returns only what matters.

Repository mentioned: https://github.com/microsoft/fastcontext (author's
note: apparently removed/private at recording time, but should come back)

## Transcript

Hey everyone, today I'm here to talk about FastContext, a free skill from
Microsoft, of all people, that's going to help us save a lot of tokens. The
idea is pretty simple. Instead of the main AI model we use when we're
coding, building something with AI, searching directly in the context, it's
going to use a subagent to look at what we need in the context, right?
Because every AI keeps generating context with every prompt we send. And
that makes this subagent spend fewer tokens, because it's only meant to
search for things in the context. And it can be using a different AI, a
local AI, a cheaper AI, a simpler model. You configure it that way and that
generates savings. A separate AI does the searching in the context, and a
more expensive AI, a higher-tier one, does the developing. Let's take a
look at how to install it, what this thing is, and other details, and of
course, test it in practice. Let's get to it.

Okay, first thing, this here is the repository, right? It's something
pretty new, relatively new. It's being updated constantly, there are
updates here from 3 hours ago. And this repository will be in the
description for you to see how to install it. But first I want to give a
few more details so we can give everyone context, okay? So the name of the
repository is FastContext, and folks, I'm debuting this slide style here,
so if you liked it instead of the scrawl, leave it in the comments, okay?

Okay, basically a subagent explores the repository instead of our coding
agent. So we're going to have two separate guys, and this guy, since he
only fetches information, he can be a cheaper AI that will manage to reach
the same results, because the information is all there, it just needs to
be found, right? And for those who don't know, the main agent searches
directly in the context to see if the information is already there. So
it's kind of a shortcut we have, right?

Okay, look, exploring is expensive, right? I put here that the same model
that solves the task also keeps doing grep, glob, and file reading, that
is, it basically searches in the context to find some code, something it
needs to solve the problem. Every search turns into garbage in the history
and pollutes the following reasoning, right? It keeps adding to the
context, because it keeps stacking information on top of other information.
And that naturally fills up the context. We have to clean it up from time
to time, otherwise we consume a lot of tokens.

It delegates, it doesn't explore. So the main agent will send a natural
language question to this FastContext, which is the other agent. It
explores the repository in a separate context, and will return only what
matters to the main agent — the resolver's history stays clean, no mess, no
navigation comes back to it. So this here is roughly the little diagram of
what happens under the hood when we use FastContext.

Three tools, so it doesn't execute anything, it only searches: a read tool
to read a file with line numbers; glob by pattern, so it'll discover the
file path; and grep searches using regex/regular expressions in the code.
It returns evidence, not mess — in the end, a lean block, file plus line
range, right? That's its output. For example, only what actually matters,
right? We can see here, file and line. The main agent receives a clean
context and can already go on to edit, test, or answer, whatever it needs
to do. All the navigation stays on the other side, it doesn't enter the
resolver's history. More accuracy, fewer tokens. This here is data they
reported, that there was more precision and more savings when using
FastContext.

Got it? So now, let's understand how to use it. Folks, the installation
process here isn't too complex. Here they also explain how the mechanism
works in a bit more detail, the response, like I showed. And here's the
install step, right? Depending on your operating system, it'll be a bit
more work or not. I installed it on Windows via WSL, worked fine. And you
can, for example, point it to some local Ollama model, or even a cheaper
model you have via subscription, I don't know, a Haiku, a GPT, since Codex
subscription is theoretically cheap and barely eats into your limit, you
can assign it to do this and actually code with Opus, right? So it'll take
the load off your Opus and you'll get a lot more usage, that's the idea,
okay?

So I've already installed it here, folks, and I'll just show the usage
part, right? Reminder, we're almost at the launch of our training "Stop
Fighting With AI". The sign-up link will be in the description and pinned
comment of this video so you can get access to benefits and a special
launch discount, okay? In this training, for those who don't know, I'll
explain my methods for how I develop projects, so you'll learn in practice
how I do it so you can apply it too and save tokens, which is the point of
this video here. You'll also manage to reach your goal faster, understand
how I think when developing my projects, since I do this basically all day,
and as a result, ship your idea. Got it?

Okay, I'm here with the project open, folks. And look, FastContext will be
running in parallel, right? It'll be running on your computer. So it'll
already be pre-configured, and when you run something like this prompt
here, where I'm activating it directly, it should respond. So I'm using the
FastContext path here, asking something, where's the authentication logic
and what would I need to change to accept login via token. This will make
it access FastContext and bring us the answer as it would to it, right? So
here I'm running FastContext directly. So see here, the AI will receive
this here, final answer. So it'll receive the files that matter most for it
to make the decision based on the question I asked. So the AI that will
ask this question, right? But anyway, we can see it's working.

To use it with the AI, you'll fire up your Claude Code or whatever, and
you'll need to configure a skill. Because the skill, this one here, look,
FastContext, is also in the repository, and part of the installation is
teaching this skill. It shows how the AI is going to use FastContext,
okay? So it kind of instructs it for that. And then, after FastContext is
installed, configured, right, with a smaller AI, with the skill placed in
your project, you'll write prompts that will naturally develop your
project, and as FastContext needs to be triggered, it will be, because
there'll be a skill ready for use.

And what happens then? It's a skill, it can be activated or not, right? If
you're implicit about it, or you can use the slash command to activate it,
right? Or you can use a prompt being explicit, saying its name, and the
agent will find and use it. So there are these three ways. The implicit one
doesn't guarantee it'll be used, so you have to be careful to activate it
at the right time or create some rule in your project, maybe in the
CLAUDE.md, explaining that if it needs to search in the context, use
FastContext. So doing it explicitly like this will definitely work.

I asked it here to use this FastContext to find out where the
authentication flow is. It'll load the skill. I'm seeing it doing that, and
under the hood, it's also activating FastContext to access the context and
bring the answer back to Claude Code. You can even test the response with
and without it to see that it even reduces response time, right? I did
these isolated tests here, I managed to get faster answers using
FastContext. So look, it already returned, right? So here we have access
to the final answer. And here it brought me everything related to the
question. And now my agent has exactly this answer to work with. In this
case it would be authentication.

So, just to give you an example here, it took about 40 seconds. I'll ask
the same question here in another terminal, right, so we can understand if
it takes a bit longer. So, it's the same thing, right? The same question,
oops, here it just duplicated, right? Let me fix it and let's see if it
takes a bit longer. So here it'll have to go into the context, search for
things. If it's not there, it'll go access the files. So it'll do
everything via, right? Here in this case number one that we did, it used
the other AI I have configured to generate the context-search part that
belongs to FastContext. And then it handed it off to Opus to form the
final answer. Just so you understand. And it took 40 seconds here.

When I'm here without FastContext, naturally it should take longer. So
here, look, it's already gone past. And of course it was a simple question,
right? The more complexity, the more time and token gain we're going to
have. That's obvious. So I see here, it's already past 50, I did a test
here of the same question, right, just one asking it to use FastContext
and the other not. And it took much longer and I spent a lot more tokens
in the process too, because here it used the more advanced AI, and here it
did a split, right, a bit with the AI that's in FastContext and a bit with
the Opus that's in Claude Code. So just with this we already have a pretty
clear example, right, of time and token gains.

Okay, folks, now I know some people are going to comment that it wasn't
exactly the same prompt. So I went ahead and already did this, got ahead
of it, right? I put the same prompt, I only added a comma and asked it to
use FastContext to help with the search. Okay, and this here was the
result. So, it really was a little bit more than the first example, but
still had, I don't know, 40-something seconds of advantage using
FastContext for the same result. Got it?

So it's a skill that will really help you save tokens, get faster answers,
but it requires a bit of setup to get it running. Reminder again, right,
you can put a smaller model that's in your subscription, right? For
example, you subscribe to Claude, it needs access to Sonnet, to Haiku, you
can delegate this to those models. And the same goes for Codex, put smaller
versions than GPT 5.5. And the best possible scenario would still be to put
a local model so it had this responsibility and could handle the requests
made against the codebase, right? Here in the repository they even
recommend a small model for this, right? So you can install this model and
test it, right? It'll depend on whether it fits on your PC and so on, but
it's not a big model and it'll get the job done because it's a model
recommended by Microsoft itself for using FastContext. Okay?

This model I just mentioned, you'll find it on Hugging Face, right, you'll
be able to download it and see if it works better, right, than using a
paid model. But, look, try to use either models you already subscribe to,
just smaller ones, or, I don't know, free models, right, sometimes we have
something on OpenRouter, you can get creative on this point, right? There's
no excuse, because you'll definitely manage to save tokens. And the more
AI gets trained, skills are going to be used implicitly more and more,
right? You'll manage to get good savings without needing to keep invoking
the skill all the time, keep that in mind. So that's the suggestion for
you all. Okay, folks?

Okay, reminder, right? Don't forget, sign up for "Stop Fighting With AI".
If you're getting bad results, regardless of the AI, if you can't reach the
point you want in your vibe-coded projects, this training here is the
solution, super practical. We're going to build the project together,
prompts, strategies from start to finish.

Okay, folks, so that was it about FastContext. I hope you enjoyed it.
Don't forget, leave a like, subscribe if you haven't. It helps us a lot,
and of course, put it in your comments so we can chat, understand if you've
already used it, if it paid off for you, anyway, let's chat down there.
I'll wrap up here, and of course, see you in the next video. Cheers!

## Timestamps (from the original video)

- 00:00 — FastContext can save you A LOT of tokens
- 01:00 — How FastContext works
- 03:40 — How to install FastContext
- 05:15 — How to use FastContext
- 08:20 — Prompt comparison WITH and WITHOUT FastContext
- 11:00 — Final thoughts on FastContext
