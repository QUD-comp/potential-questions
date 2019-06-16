#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import spacy
import re
import random
from nltk.corpus import propbank
from itertools import islice
import pandas as pd

class QuestionMaker():
	def __init__(self):
		self.nlp = spacy.load('en')
		self.question_dict={}
		self.datapath = 'q_temps.tsv' 
		self.df = pd.read_csv(self.datapath, sep = '\t') # load question templates from tsv
		self.df.columns = ['Q', 'POS', 'TAG']
		self.aux_list = ['aux', 'auxpass', 'ROOT', 'advcl', 'ccomp', 'conj']
		self.verb_list = ['VBG', 'VBN', 'VBD', 'VBP', 'VBZ', 'VB']
		self.subj_list = [ 'nsubj', 'nsubjpass', 'expl','csubj','csubjpass']
		self.obj_list = ['obj', 'dobj', 'pobj']
		self.conj_list = ['CC', 'IN']
		self.indefinites = ['a', 'an']
		self.time_list = ['DATE', 'TIME','WRB']
		self.aux_dict = {'VBD': ['did', 'do', 'VBD', 'O', '', 'aux'],'VBP': ['do', 'do', 'VB', 'O', '', 'aux'], 'VBZ': ['does', 'do', 'VBZ', 'O', '', 'aux']}
		self.pro_dict = {'mine': 'yours', 'yours': 'mine', 'ours': 'yours', 'we': 'you', 'We': 'you', 'my': 'your', 'our': 'your', 'your': 'my', 'myself': 'yourself', 'ourself': 'yourself', 'yourself': 'myself', 'me': 'you', 'mine': 'yours', 'yours': 'mine', 'ours': 'yours', 'i': 'you'}
		self.pro_dict2 = {'she': 'her', 'he': 'him', 'they': 'them', 'her': 'her', 'him': 'him', 'them': 'them'}
		self.personal_nouns = ['PERSON', 'ORG']
		self.prep_list = ['at','for','to','on','by','with','in','from','into','about','behind','against','of','as']
		self.pb_inst = propbank.instances()
		self.verb_dict = {self.pb_inst[i].roleset[:-3]:i for i,item in enumerate(self.pb_inst)} # get verbs and their position in propbank list

	def return_tags(self, s):
		parsed_s = self.nlp(s)
		return [[str(X).lower(), X.lemma_, X.tag_, X.ent_iob_, X.ent_type_, X.dep_] if X.ent_iob_ == 'O' else [str(X), X.lemma_, X.tag_, X.ent_iob_, X.ent_type_, X.dep_] for X in parsed_s]	

	def you_and_me(self, s): 
		sentlist = s.split()
		for i, word in enumerate(sentlist):
			if word.lower() == 'i' and sentlist[i+1].lower() == 'am':
				sentlist[i] = 'you'
				sentlist[i+1] = 'are'
			elif word.lower() == 'you' and sentlist[i+1].lower() == 'are':
				sentlist[i] = 'I'
				sentlist[i+1] = 'am'
			elif word.lower() == 'i' and sentlist[i+1].lower() == 'was':
				sentlist[i] = 'you'
				sentlist[i+1] = 'were'
		return ' '.join(sentlist)

	def change_view(self, s): 
	# switch personal pronouns etc first-second person 
		for word in s:
			if word[2] in ['PRP','PRP$','NNS','NN']:
				if str(word[0]).lower() in self.pro_dict:
					word[0] = self.pro_dict[str(word[0]).lower()]
		return s

	def set_verb(self, s):
	# add auxiliary for subject-aux reversal
		for i,tup in enumerate(islice(s, len(s))):
			if tup[5] == 'aux':
				return s
			if tup[2] in self.aux_dict and tup[1] != 'be':
				tup[0] = tup[1]
				ss = s[:i] + [[x for x in self.aux_dict[tup[2]]]] + [[y for y in tup]] + s[i+1:]
				return ss
		return s

	def reverse_subj_aux(self, t):
	# find subject and switch subj and aux
		for i, tup in enumerate(islice(t, len(t)-1)):
			if tup[5] in self.subj_list and t[i+1][5] in self.aux_list:
				tags = [item[2] for item in t[:i+1]]
				subject_pattern = re.findall(r'(?:DT|PRP\$)? ?(?:JJ[R|S]? )*(?:NN[PS]*|PRP) ?(?:IN )?(?:NN[PS]* ?)*',' '.join(tags))
				if subject_pattern not in [[], None]:
					subj_tags = [tag for tag in subject_pattern[0].split()]
					subj_start = tags.index(subj_tags[0])
					subj_end = tags.index(subj_tags[-1])+1
					new_order = t[:subj_start] + t[i+1:i+2] + t[subj_start:subj_end] + t[i+2:]
					return new_order
		return t

	def specify_subj(self, s):
	# if subject is underspecified, ask for more information
		qs = []
		for i, tup in enumerate(s):
			if tup[5] in self.subj_list:
				tags = [item[2] for item in s[:i+1]]
				pattern = list(zip(range(len(tags)),tags))
				no_pattern = ([tup[1]+str(tup[0]) for tup in pattern])
				pattern_dict = dict(zip(no_pattern, range(len(tags))))
				subject_pattern = re.search(r'(?:JJ[R|S]?[0-9]+ )*(?:(?:NNS*|EX)[0-9]+) ?(?:IN[0-9]+ )?(?:NNS*[0-9] ?)*',' '.join(no_pattern))
				if subject_pattern not in [[], None]:
					subj_tags = subject_pattern.group().split()
					subj_start = pattern_dict[subj_tags[0]]
					subj_end = pattern_dict[subj_tags[-1]]
					if s[subj_start-1][2] not in ['DT','PRP$']:
						qs.append('Which ' + ' '.join([word[0] for word in s[subj_end:]]) + '?')
					elif s[subj_start-1][0].lower() in self.indefinites:
						qs.append('Which ' + ' '.join([word[0] for word in s[subj_end:]]) + '?')
		return qs

	def specify_obj(self, s):
	# if object is underspecified, ask for more information
		qs = []
		for i, tup in enumerate(s):
			if tup[5] in self.obj_list and not tup[2] == 'PRP':
				tags = [item[5] for item in s[:i+1]]
				pattern = list(zip(range(len(tags)),tags))
				no_pattern = ([tup[1]+str(tup[0]) for tup in pattern])
				pattern_dict = dict(zip(no_pattern,range(len(tags))))
				object_pattern = re.search(r'(?:nummod([0-9]+) )?(?:amod([0-9]+),?(?: cc([0-9]+) conj([0-9]+))* )*(?:compound([0-9]+) )?(?:(?:obj|pobj|dobj)([0-9]+))',' '.join(no_pattern))
				if object_pattern not in [[], None]:
					obj_tags = object_pattern.group().split()
					obj_start = pattern_dict[obj_tags[0]]
					obj_end = pattern_dict[obj_tags[-1]]
					if s[obj_start-1][2] not in ['DT','PRP$']:
						qs.append('Which ' + ' '.join([word[0] for word in s[obj_start:i+1]]) + ' ' + ' '.join([word[0] for word in s[:obj_start]]) + '?')
					elif s[obj_start-1][0].lower() in self.indefinites:
						qs.append('Which ' + ' '.join([word[0] for word in s[obj_start:i+1]]) + ' ' + ' '.join([word[0] for word in s[:obj_start-1]]) + '?')
						qs.append('What is the ' + ' '.join(word[0] for word in s[obj_start:i+1]) + ' about?')
		return qs

	def subcategorization(self, s):
		qs = []
		objects = [word for word in s if word[5] in self.obj_list]
		for word in s: 
	#		print(word[1])
			if word[2] in self.verb_list and not word[1] == 'be':
	#			print(word[1])
				if word[1] in self.verb_dict.keys():
					roles = [tup[1] for tup in self.pb_inst[self.verb_dict[word[1]]].arguments]
	#				print('ROLES for %s: %s' % (word[1],roles))
					if 'ARG0' in roles:
						roles.remove('ARG0')
					if 'ARGM-MNR' in roles:
						qs.append('How ' + ' '.join([word[0] for word in s]) + '?')
					if len([role for role in roles if role in ['ARG1', 'ARG2']]) > len(objects):
						qs.append('What ' + ' '.join([word[0] for word in s]) + '?')
					for prep in self.prep_list:
						if prep in re.findall(r'-([a-z]+)', ' '.join(roles)):
							sent_list = [word[0] if not word[0] in self.indefinites else 'the' for word in s]
							if not prep in sent_list:
								if prep == 'at':
									qs.append('Where ' + ' '.join(sent_list) + '?')
								else:
									qs.append('What ' + ' '.join(sent_list) + ' ' + prep + '?')
									qs.append('Who ' + ' '.join(sent_list) + ' ' + prep + '?')
		return qs

	def ne_questions(self, s):
		nes = []
		s = s[::-1]	#get Multiword Expressions
		pattern = [word[3] for word in s]
		for j,sym in enumerate(pattern):
			if sym == 'B':
				if s[j][2] == 'DT':
					s[j][2] = s[j+1][2]
			if sym == 'I':
				s[j+1][0] = s[j+1][0] + ' ' + s[j][0]
				s[j][4] = ''
		s = s[::-1] 
		tags = {tag[0]: (tag[4],tag[2]) for tag in s if not tag[4] == ''}
		questions = []
		for name, tup in tags.items():
			df_selection = self.df[(self.df.TAG == tup[0]) & (self.df.POS == tup[1])]
			qlist = df_selection['Q']
			qs = []
			for ql in qlist:
				new = ql.replace(tup[0], name)	#replace tag in template with word 
				qs.append(new)
			nes.append(qs)
		return nes

	def why(self, s):	
		q = []
		if s[0][5] in self.aux_list:
			q.append('Why ' + ' '.join([word[0] if not word[0] in self.indefinites else 'the' for word in s]) + '?')
		return q

	def where(self, s):
		q = []
		to_delete = []
		if s[0][5] in self.aux_list:
			for i, word in enumerate(s):
				if word[0] == 'there' and not word[2] == 'EX':
					to_delete.append(i)
		for index in to_delete:
			del s[i]
			q.append('Where exactly ' + ' '.join([word[0] if not word[0] in self.indefinites else 'the' for word in s]) + '?')
		return q

	def when(self, s):
		q = 'When ' + ' '.join([word[0] if not word[0] in self.indefinites else 'the' for word in s]) + '?'
		return q

	def animacy(self, s):
		qlist = []
		for word in s: 
			if word[4] in self.personal_nouns:
				qlist.append('What else do we know about %s?' % word[0])
			elif word[0].lower() in self.pro_dict2.keys():
				qlist.append('What else do we know about %s?' % self.pro_dict2[word[0].lower()])
		return qlist

	def ask_source(self, s):
		return 'How do you know that %s?' % ' '.join([word[0] for word in s])

	def simplify_nested(self, s):
		tags = [word[5] for word in s]
		for i, tag in enumerate(tags):
			if tag in self.subj_list:
				j = i
				commas = 0
				while j < len(tags):
					if tags[j] == 'punct':
						commas +=1
					elif tags[j] in self.aux_list and commas%2 == 0:
						return s[:i+1] + s[j:]
					j += 1
			return s

	def separate_matrix(self, sent):
		s = []
		def separate(s_):
			tags = [word[5] for word in s_]
			if 'mark' not in tags:
				s.append(s_)
			elif 'mark' in tags:
				separate(s_[:tags.index('mark')])
				separate(s_[tags.index('mark')+1:])
		separate(sent)
		return(s)

	def removal(self, sent):
		chopped = []
		def remove_adjuncts(s):
			tags = [word[5] for word in s]
			if 'punct' not in tags:
				chopped.append(s)
			else:
				new1, new2 = s[:tags.index('punct')], s[tags.index('punct')+1:]
				for new in [new1, new2]:
					if any(set(self.subj_list) & set([t[5] for t in new])) and any(set(self.aux_list) & set([t[5] for t in new])):
						remove_adjuncts(new)
					else: pass
		remove_adjuncts(sent)
		return chopped

	def remove_conj(self, s): #this is a miscellaneous method that removes all adverbs except for 'there', as well as leading conjunctions and prepositional phrases 
		to_delete = []
		for i, word in enumerate(s):
			if word[5] == 'advmod' and word[2] == 'RB' and not word[0].lower() == 'there':
				to_delete.append(i)
				if s[i-1][2] == ',' and s[i+1][2] == ',':
					to_delete.append(i-1)
		if s[0][2] == 'CC':
			to_delete.append(0)
		if s[0][2] == 'IN':
			deps = [word[5] for word in s]
			subj = [tag for tag in deps if tag in self.subj_list]
			index = deps.index(subj[0])
			for i in range(index):
				to_delete.append(i)
		new_s = [word for word in s if not s.index(word) in to_delete]
		return new_s

	def split_at_and(self, sent):
		s = []
		def split(s_):
			tags = [word[2] for word in s_]
			if 'CC' not in tags:
				s.append(s_)
			else:
				sub1, sub2 = s_[:tags.index('CC')], s_[tags.index('CC')+1:]
				try:				
					if sub1[0][5] in self.subj_list and any(set(self.aux_list) & set([w[5] for w in sub1])) and sub2[0][5] in self.subj_list and any(set(self.aux_list) & set([w[5] for w in sub2])):
						split(sub1)
						split(sub2)
					else: 
						s.append(s_)	
				except IndexError:
					s.append(s_)
		split(sent)
		return s

	def make_questions(self, s):
		SourceQs = []
		WhyQs = []
		SubQs = []
		WhereQs = []
		AniQs = []
		WhenQs = []
		NEQs = []
		SpecQs = []
		switch_you_me = self.you_and_me(s)
		tagged_sent = self.return_tags(switch_you_me)
		split_matrix_sent = self.separate_matrix(tagged_sent)
		for s_ in [s for s in split_matrix_sent if not s in [[], None]]:
			ands_removed = self.split_at_and(s_)
			for s__ in [s for s in ands_removed if not s in [[], None]]:
				simplified_nested = self.simplify_nested(s__)
				partial_sentences = self.removal(simplified_nested)
				for s___ in [s for s in partial_sentences if not s in [[], None]]:
					removed_conjs = self.remove_conj(s___)
					changed_pronouns = self.change_view(removed_conjs)
					source_q = self.ask_source(changed_pronouns)
					SourceQs.append(source_q)
					added_aux = self.set_verb(changed_pronouns)
					reversed_subj = self.reverse_subj_aux(added_aux)
					why_q = self.why(reversed_subj)
					WhyQs.append(why_q)
					if not any(set(self.time_list) & set([word[4] for word in tagged_sent] + [word[2] for word in tagged_sent])):
						when_q = self.when(reversed_subj)
						WhenQs.append(when_q)
					where_q = self.where(reversed_subj)
					WhereQs.append(where_q)
					sub_q = self.subcategorization(reversed_subj)
					SubQs.append(sub_q)
					ne_q = self.ne_questions(reversed_subj)
					NEQs.append(ne_q)
					ani_q = self.animacy(reversed_subj)
					AniQs.append(ani_q)
					speco_q = self.specify_obj(reversed_subj)
					spec_q = self.specify_subj(changed_pronouns)
					SpecQs.append(spec_q)
					SpecQs.append(speco_q)
		return SubQs, WhereQs, WhyQs, WhenQs, AniQs, SpecQs, SourceQs, NEQs	

	def ask_random_q(self, s):
		questions = self.make_questions(s)
		qs = self.flatten(questions)
		Qs = [q for q in qs if q is not None]
		i = random.randint(0,len(Qs)-1)
		return qs[i]

	def flatten(self, S):
		S = list(S)
		if S == []:
			return S
		if isinstance(S[0], list):
			return self.flatten(S[0]) + self.flatten(S[1:])
		return S[:1] + self.flatten(S[1:])
