# -*- coding: utf-8 -*-
# file: evolution.py
# time: 2021/7/30
# author: yangheng <yangheng@m.scnu.edu.cn>
# github: https://github.com/yangheng95
# Copyright (C) 2021. All Rights Reserved.
import random

from DaNuoYi.deep_learning.classifier.fitness_assigner import FitnessAssigner
from DaNuoYi.deep_learning.translator.translator import InjectionTranslator
from DaNuoYi.evolution.entity.individual import Individual
from DaNuoYi.evolution.entity.population import Population
from DaNuoYi.utils.bypass import is_bypass

from DaNuoYi.global_config import MODSECURITY_WAF, NGX_LUA_WAF, LUA_RESTY_WAF, OPEN_WAF

from DaNuoYi.global_config import REGENERATE_COUNT


class SingleTaskEvolution:
    def __init__(self, args, logger, rnd_select, no_mutation):
        self.task = args.tasks[0]
        self.pop = Population(self.task, args.pop_size)
        self.bypass_injection_by_task = {task: set() for task in args.tasks}
        self.count_by_task = {task: 0 for task in args.tasks}

        self.fitness_assigner = FitnessAssigner(self.task, logger.classifier)
        self.fitness_assigner.assign_fitness(self.pop)

        self.logger = logger

        self.rnd_select = rnd_select
        self.no_mutation = no_mutation

        if args.waf == 'mod_security':
            self.waf_address = MODSECURITY_WAF
        elif args.waf == 'ngx_lua_waf':
            self.waf_address = NGX_LUA_WAF
        elif args.waf == 'lua_resty_waf':
            self.waf_address = LUA_RESTY_WAF
        elif args.waf == 'open_waf':
            self.waf_address = OPEN_WAF
        else:
            raise KeyError('Unimplemented WAF: {}!'.format(args.waf))

        self.visited = set()

    def evolve(self, gen_id):
        avg_fitness = self.pop.get_average_fitness()
        _pop = self.pop[:]
        for i in range(len(self.pop)):
            idv = self.pop[i].mutate()
            while idv.injection in self.visited:
                idv = Individual(idv.task)

            self.visited.add(idv.injection)

            self.fitness_assigner.assign_fitness(idv)

            if is_bypass(idv, self.waf_address) and idv.injection not in self.bypass_injection_by_task[self.task]:
                self.count_by_task[self.task] += 1
                self.bypass_injection_by_task[self.task].add(idv.injection)

            _pop.append(idv)
            # if not rnd_select:
            #     if idv.fitness > avg_fitness:
            #         _pop.append(idv)
            #     else:
            #         _pop.append(Individual(idv.task))

        if not self.rnd_select:
            self.fitness_assigner.assign_fitness(_pop)
            _pop = sorted(_pop, key=lambda x: x.fitness, reverse=True)
        else:
            random.shuffle(_pop)

        self.pop.individuals = _pop[:len(self.pop)]
        self.logger.log_count(self.count_by_task, gen_id)


class MultiTaskEvolution:
    def __init__(self, args, logger, rnd_select, no_mutation):
        self.tasks = args.tasks
        self.pops = {t: Population(t, args.pop_size) for t in args.tasks}
        self.bypass_injection_by_task = {task: set() for task in args.tasks}
        self.count_by_task = {task: 0 for task in args.tasks}

        self.translators = {}
        for t1 in self.tasks:
            for t2 in self.tasks:
                if t1 != t2:
                    self.translators['{}2{}'.format(t1, t2)] = InjectionTranslator(t1, t2)

        self.fitness_assigners = {t: FitnessAssigner(t, logger.classifier) for t in self.tasks}

        for task in self.tasks:
            self.fitness_assigners[task].assign_fitness(self.pops[task])

        self.logger = logger
        self.rnd_select = rnd_select
        self.no_mutation = no_mutation

        if args.waf == 'mod_security':
            self.waf_address = MODSECURITY_WAF
        elif args.waf == 'ngx_lua_waf':
            self.waf_address = NGX_LUA_WAF
        elif args.waf == 'lua_resty_waf':
            self.waf_address = LUA_RESTY_WAF
        elif args.waf == 'open_waf':
            self.waf_address = OPEN_WAF
        else:
            raise KeyError('Unimplemented WAF: {}!'.format(args.waf))

        self.visited = set()

    def evolve(self, gen_id):
        
        src_mut_dict = {}
        src_mut_dict['src'] = {}
        src_mut_dict['trans'] = {}
        src_dest_dict = {}
        for pop_name in self.pops:
            src_dest_dict[pop_name] = {}
            avg_fitness = self.pops[pop_name].get_average_fitness()
            _pop = self.pops[pop_name][:]
            for i in range(len(self.pops[pop_name])):
                payload = self.pops[pop_name][i].injection
                mutated_idv, mutated_flag = self.perform_mutate(i, pop_name)
                mutated = mutated_idv.injection
                src_mut_dict = self.src_mut_translation(payload, mutated, pop_name, src_mut_dict)
                idv, flag, src_payload = self.perform_translate(pop_name, len(self.pops[pop_name]))
                if not flag:
                    if self.no_mutation:
                        idv = Individual(pop_name)
                        src_payload = None
                    else:
                        idv, flag = self.perform_mutate(i, pop_name)
                        src_payload = None

                if not self.rnd_select:
                    if idv.fitness > avg_fitness:
                        _pop.append(idv)
                    else:
                        _pop.append(Individual(idv.task))
                        src_payload = None
                        
                if src_payload is not None:
                    src_dest_dict[pop_name][f'{idv.injection}'] = src_payload

            if not self.rnd_select:
                self.fitness_assigners[pop_name].assign_fitness(_pop)
                _pop = sorted(_pop, key=lambda x: x.fitness, reverse=True)
            else:
                random.shuffle(_pop)
            self.pops[pop_name].individuals = _pop[:len(self.pops[pop_name])]

        self.logger.log_count(self.count_by_task, gen_id)
        self.logger.write_dict_to_file(src_dest_dict, 'src_dest_dict')
        self.logger.write_dict_to_file(src_mut_dict, 'src_mut_dict')

    def perform_translate(self, pop_name, length):
        idv, src_payload = self.translate(pop_name, length)

        count = REGENERATE_COUNT
        while idv.injection in self.visited and count:
            idv = Individual(idv.task)
            count -= 1

        if is_bypass(idv, self.waf_address) and idv.injection not in self.bypass_injection_by_task[pop_name]:
            self.count_by_task[pop_name] += 1
            self.bypass_injection_by_task[pop_name].add(idv.injection)
            self.fitness_assigners[pop_name].assign_fitness(idv)
            self.visited.add(idv.injection)
            return idv, True, src_payload

        self.fitness_assigners[pop_name].assign_fitness(idv)
        self.visited.add(idv.injection)
        return idv, True, src_payload

    def perform_mutate(self, idx, pop_name):
        idv = self.pops[pop_name][idx].mutate()

        count = REGENERATE_COUNT
        while idv.injection in self.visited and count:
            idv = Individual(idv.task)
            count -= 1

        if is_bypass(idv, self.waf_address) and idv.injection not in self.bypass_injection_by_task[pop_name]:
            self.count_by_task[pop_name] += 1
            self.bypass_injection_by_task[pop_name].add(idv.injection)
            self.fitness_assigners[pop_name].assign_fitness(idv)
            self.visited.add(idv.injection)
            return idv, True

        self.fitness_assigners[pop_name].assign_fitness(idv)
        self.visited.add(idv.injection)
        return idv, False

    def translate(self, pop_name, length):
        _other_tasks_ = self.tasks[:]
        _other_tasks_.remove(pop_name)
        select_task_name = random.choice(_other_tasks_)
        idx = random.randint(0, length - 1)
        src_payload = self.pops[select_task_name][idx].injection
        # translate
        translator_name = '{}2{}'.format(select_task_name, pop_name)
        idv = Individual(pop_name)
        idv.injection = self.translators[translator_name].translate(src_payload)
        return idv, src_payload
    
    def src_mut_translation(self, payload, mutated, pop_name, src_mut_dict):
        _other_tasks_ = self.tasks[:]
        _other_tasks_.remove(pop_name)
        select_task_name = random.choice(_other_tasks_)  # works just for double task
        # translate
        translator_name = '{}2{}'.format(pop_name, select_task_name)
        payload_translated = self.translators[translator_name].translate(payload)
        mutated_translated = self.translators[translator_name].translate(mutated)
        
        if payload not in src_mut_dict['src'].keys() and payload_translated not in src_mut_dict['trans'].keys():
            src_mut_dict['src'][f'{payload}'] = mutated
            src_mut_dict['trans'][f'{payload_translated}'] = mutated_translated

        return src_mut_dict
