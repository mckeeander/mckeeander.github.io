# What 798 Films Say About Representation and Revenue

**Ander McKee** · DSC 530 Data Exploration and Analysis · Final Project, Part 2

## The problem

The film industry has a standing assumption that female-led stories are a
commercial risk. That assumption shapes budgets, and budgets shape what gets made.
I wanted to know whether the data supports it.

The Bechdel test asks three things of a film: are there two named women, do they
talk to each other, and do they talk about something other than a man. It is a low
bar, and clearing it says little about quality. But it is measured consistently
across thousands of films, which makes it usable. My question was simple: among US
films released between 1990 and 2015, do films that pass earn less than films that
fail?

## The data

I built one analysis table from three independent public sources. The Pudding's
film dialogue data supplied character-level word counts coded by gender.
bechdeltest.com supplied volunteer-assigned Bechdel ratings. The Numbers supplied
production budgets and box office grosses. Joining them left **798 films**.

The joins cost me something, and it matters. Mean inflation-adjusted gross rose
from \$93M to \$106M to \$125M across the three merge stages. Every join kept the
larger films. So this sample describes well-documented commercial releases, not
films in general — a limitation I carried through the whole analysis rather than
noting once and forgetting.

## The finding that wasn't there

I started with the obvious test. Split the films into passing and failing, compare
mean domestic gross, run a t-test.

Nothing. Passing films earned 3.1% less, with p = 0.728. A Mann-Whitney U test
agreed at p = 0.409. On its face, representation and revenue looked unrelated.

That result is where a lot of analyses would stop. It would have been wrong to stop
there.

## The finding that appeared

The bivariate work had already turned up something the t-test couldn't see. Budget
correlates with gross at r = 0.652 — bigger films earn more, which is unsurprising.
But budget also correlates *negatively* with Bechdel rating. Films rated 0 have a
median budget of \$62M. Films rated 3 have a median budget of \$35M.

That is a suppressor. Passing films are handed less money, less money earns less
revenue, and that downward pull cancels out whatever else is happening. The raw
comparison was measuring two opposing effects at once and reporting the sum as
zero.

So I ran the same comparison holding budget and release year fixed.

![Budget declines as Bechdel rating rises, and controlling for it reverses the headline result](figures/narrative_suppression.png)

Passing the Bechdel test is associated with **21.7% higher domestic gross** at
fixed budget and year (95% CI +6.3% to +39.3%, p = 0.004). One control flipped a
null result into a clear positive one. The specification was locked in writing
before any model ran, so this isn't a number I searched for. It held across all
four pre-declared robustness checks: worldwide gross (+20.9%), inflation-adjusted
gross (+18.5%), and genre controls (+17.4%).

Put plainly: **films that pass earn more than films of comparable cost.** They are
simply given less to work with.

## Three methods, one story

What convinced me this is real is that separate techniques kept landing on the same
relationship.

A **logistic regression** tried to predict whether a film passes from how it was
packaged — genre, MPAA rating, budget, and release year. It managed 59% accuracy
against a 50% baseline. That near-failure is the result: you cannot tell whether a
film represents women from its commercial profile. The little signal there is comes
from category rather than money, and one genre stands out. Horror films pass at
74%, nearly double Action's 38%.

**k-means clustering** found three groups without ever seeing the Bechdel ratings.
When I checked them afterward, pass rates ran 36%, 44%, and 87%.

![Clusters found without Bechdel data still separate cleanly by Bechdel outcome](figures/final_clusters.png)

The third cluster is mid-budget films where women speak 57% of the dialogue. The
other two are separated almost entirely by money, and both give women under a
quarter of the lines. Being a small, cheap film does not make a film female-forward
— that was the most surprising thing I found.

A **random forest** was the one method that added nothing. It scored worse than
ordinary least squares under cross-validation (R² 0.366 vs 0.441), because after a
log transform the relationship is genuinely linear and flexibility bought nothing.

## Recommendations

**For studios and financiers.** The budget gap between passing and failing films is
not justified by their returns. Passing films in this sample outperformed
comparably budgeted films by roughly a fifth. If a \$35M film returns what a \$62M
film returns, the \$35M film is the better investment, and the current allocation
is leaving money unclaimed.

**Do not screen for representation using commercial signals.** Genre, rating,
budget, and release year together predict Bechdel outcomes barely better than
chance, and the financial variables are the weakest of the four. Any process
inferring representation from how a film is packaged is guessing. It has to be
measured.

**Fund the interaction, not the word count.** Female dialogue *share* showed no
association with revenue (+0.7% per 10 points, p = 0.72). The Bechdel *threshold*
did. Two women speaking to each other is the thing that tracks, not the raw volume
of women's dialogue.

**For analysts.** Check for suppression before you report a null. My unadjusted
t-test would have supported exactly the conclusion the data contradicts.

## What this does not show

This is association, not causation. Nothing here says that changing a script would
change a film's revenue — passing and failing films likely differ in ways budget and
year don't capture. The sample skews toward larger commercial releases, gender
coding is binary, ratings come from volunteers rather than trained coders, and the
confidence interval is wide enough that the direction is firmer than the magnitude.

The claim I'll defend is narrow and I think it holds: **within this sample, the
commercial penalty for representation shows up in what films are given, not in what
they earn.**
