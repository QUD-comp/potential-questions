# Generating potential questions
project of potsdam university

given a certain context (a sentence), we want to generate potential follow-up questions. these have to be ranked by the complementary module 'ranking potential questions'. the application can be used in chatbot systems, for instance.

## data

the question templates are taken from the [yahoo answers factoid queries dataset](https://webscope.sandbox.yahoo.com/catalog.php?datatype=l&did=76). duplicates and questions which contained more than one named entity were removed. the (very small) test set is taken from onea's 2013 [thesis *potential questions in discourse and grammar*](https://www.researchgate.net/publication/280010537_Potential_Questions_in_Discourse_and_Grammar) and from the snowden interview

## usage

the question maker can be used directly in the jupyter notebook or by importing the python script

```python
from questionmaker import QuestionMaker

qm = QuestionMaker()
qm.ask_random_q('I love strawberries')
```
## output

```bash
'Why do you love strawberries?'
```
