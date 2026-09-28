"""R2-F2/F3 corrective properties against the selected candidate, including fail-before.

The oracle is absence of the literal protected inputs, not a production-generated expected answer.
Safe controls preserve ordinary attribution; command-tail arguments remain outside wrapper collection.
"""
import os
from pathlib import Path
import random
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOL=Path(os.environ.get('V2E_EVIDENCE',ROOT/'skills/vibe-to-engineering/scripts/evidence.py'))
sys.path.insert(0,str(TOOL.parent))
import emission


class CorrectiveEmission(unittest.TestCase):
    def assert_private(self,text,values):
        result=emission.scrub(text,values)
        for value in values:
            if value and not emission.unmaskable(value): self.assertNotIn(value,result)
        self.assertLess(len(result),len(text)*100+1000,'bounded output, not replacement growth')
        return result

    def test_replacement_edges_never_recreate_a_longer_value(self):
        for left,right in [('left931','right931'),('left932',''),('','right933')]:
            for small in ('X','9','masked'):
                for marker in ('<masked>','!'*64):
                    large=left+marker+right
                    for values in ([large,small],[small,large]):
                        with self.subTest(left=left,right=right,small=small,marker=marker,order=values):
                            self.assert_private(left+small+right,values)

    def test_generated_overlaps_and_marker_collisions(self):
        rng=random.Random(943)
        for i in range(160):
            values=rng.sample(['a','ab','aba','bab','baba','masked','<','>','_','7','77','a<masked>b',
                               'left<masked>right','!','!!','é','λ'],rng.randint(1,7))
            text='left'+''.join(rng.choice(['a','b','7','<masked>','é','λ']) for _ in range(24))+'right'
            with self.subTest(i=i): self.assert_private(text,values)

    def test_exhausting_ascii_marker_letters_still_keeps_values_private(self):
        values=[chr(n) for n in range(33,127) if chr(n)!='=']
        self.assert_private('a<masked>7 ordinary output',values)

    def test_normal_replacements_and_safe_text_stay_readable(self):
        result=emission.scrub('keep plain before abc931 and abc931-long after',['abc931','abc931-long'])
        self.assertEqual(result,'keep plain before <masked> and <masked> after')
        self.assertEqual(emission.scrub('ordinary text',[]),'ordinary text')

    def test_collect_understands_every_unique_value_option_abbreviation(self):
        for option,operand in [('--pro','p'),('--proj','p'),('--o','o'),('--ou','o'),
                               ('--w','/tools'),('--with','/tools'),('--enr','python3')]:
            for setting in (['--env','A=LaterCanary944'],['--env=A=LaterCanary944']):
                with self.subTest(option=option,setting=setting):
                    self.assertIn('LaterCanary944',emission.collect([option,operand]+setting+['--','cmd']))

    def test_missing_option_operand_does_not_consume_the_next_env_option(self):
        for option in ('--project','--out','--with-path','--enroll-runner'):
            with self.subTest(option=option):
                self.assertIn('Late945',emission.collect([option,'--env','A=Late945','--','cmd']))

    def test_command_boundaries_and_negative_option_operands(self):
        for tail in (['--','cmd','--env','B=child946'],['cmd','--env','B=child946'],
                     ['--command with space','--env','B=child946']):
            self.assertEqual(emission.collect(['--project','-1','--env','A=ours946']+tail),['ours946'])
        self.assertEqual(emission.collect(['--project=p','--env=A=ours947','--','cmd']),['ours947'])
        self.assertEqual(emission.collect(['--project','--folder with space','--env=A=ours947',
                                          '--','cmd']),['ours947'])


if __name__=='__main__': unittest.main()
