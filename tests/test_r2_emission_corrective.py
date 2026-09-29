"""Real CLI regressions for Codex's remaining R2-F2/F3/F6 findings.

All projects and HOMEs are disposable. V2E_EVIDENCE selects the frozen pre-correction tool;
the failures concern emitted bytes and missing run facts, not a new production API.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
TOOL=Path(os.environ.get('V2E_EVIDENCE',ROOT/'skills/vibe-to-engineering/scripts/evidence.py'))
sys.path.insert(0,str(TOOL.parent))
import evidence
import enrolled
from result_record import read

PY=os.path.realpath(sys.executable)


class CorrectiveCLI(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='v2e-r2-corrective-')).resolve()
        self.count=0
        self.env=enrolled.environ()
        self.registry=Path(self.env['HOME'])/'.vibe-to-engineering/runners.json'
        self.registry_before=self.registry.read_bytes()

    def tearDown(self):
        self.assertEqual(self.registry.read_bytes(),self.registry_before)
        shutil.rmtree(self.tmp)

    def case(self,body="print('ordinary output')\n",files=None,outname='check.txt'):
        self.count+=1
        project=self.tmp/('p%d'%self.count)
        out=project/'.vibe-to-engineering/evidence'/outname
        out.parent.mkdir(parents=True)
        for name,text in (files or {}).items(): (project/name).write_text(text)
        (project/'check.py').write_text("from pathlib import Path\nPath('ran').write_text('yes')\n"+body)
        return project,out

    def cli(self,project,out,flags=(),raw=None):
        args=raw if raw is not None else ['--project',str(project),'--out',str(out)]+list(flags)+['--',PY,'-B','check.py']
        done=subprocess.run([PY,'-B',str(TOOL)]+args,env=self.env,capture_output=True,timeout=30)
        printed,report=(b.decode('utf-8','replace') for b in (done.stdout,done.stderr))
        saved=out.read_text() if out.is_file() else None
        return done.returncode,printed,report,saved,(project/'ran').exists()

    def private(self,observed,values):
        for surface in observed[1:4]:
            if surface is not None:
                for value in values: self.assertNotIn(value,surface)

    def facts(self,report,wrapper,launched,saved,child):
        self.assertEqual(read(report),dict(v=1,wrapper=wrapper,launched=launched,saved=saved,child=child),report)

    def test_declared_value_created_across_summary_marker_edges(self):
        for args in (['--env','A=a<masked>b','--env','B=X'],['--env=B=X','--env=A=a<masked>b']):
            with self.subTest(args=args):
                p,out=self.case(outname='aXb.txt')
                got=self.cli(p,out,args)
                self.assertEqual(got[0],0,got[2]);self.assertTrue(got[4]);self.assertIsNotNone(got[3])
                self.private(got,['a<masked>b','X'])

    def test_recognized_file_values_are_protected_after_marker_assembly(self):
        cases=[("SECRET='left<masked V>right'\nV=xQ931\n","print('leftxQ931right')\n",'left<masked V>right'),
               ("SECRET=masked\n","print('API_KEY=otherSyntheticValue941')\n",'masked')]
        for source,body,value in cases:
            with self.subTest(value=value):
                p,out=self.case(body,{'.env':source})
                got=self.cli(p,out)
                self.assertEqual(got[0],0,got[2]);self.assertTrue(got[4])
                self.private(got,[value])

    def test_known_file_secret_is_protected_in_summary_path_and_write_failure(self):
        for writable in (True,False):
            with self.subTest(writable=writable):
                p,out=self.case(files={'.env':'SECRET=summaryCanary942\n'},outname='summaryCanary942.txt')
                if not writable: out.parent.chmod(0o555)
                try: got=self.cli(p,out)
                finally: out.parent.chmod(0o755)
                self.assertEqual(got[0],0 if writable else 1,got[2]);self.assertTrue(got[4])
                self.private(got,['summaryCanary942'])

    def test_fixed_prefix_and_help_text_use_the_full_emission_context(self):
        for flags,value,expected in [(['--env','A=evidence.py','--env','BASH_ENV=fixture-value'],'evidence.py',2),
                                      (['--env','A=error','--with-path','relative'],'error',2),
                                      (['--env','A=SHA-256','--help'],'SHA-256',0),
                                      (['--help','--env','A=evidence.py'],'evidence.py',0)]:
            with self.subTest(flags=flags):
                p,out=self.case();got=self.cli(p,out,flags)
                self.assertEqual(got[0],expected,got[2]);self.assertFalse(got[4]);self.assertIsNone(got[3])
                self.private(got,[value])

    def test_abbreviations_do_not_hide_later_values_from_duplicate_or_parser_errors(self):
        for pro,outflag in [('--pro','--out'),('--project','--ou'),('--proj','--o')]:
            for duplicate in (False,True):
                with self.subTest(pro=pro,out=outflag,duplicate=duplicate):
                    p,out=self.case()
                    flags=[pro,str(p),outflag,str(out),'--env','A=DuplicateCanary941']
                    flags+=['--env','DuplicateCanary941_X=one','--env=DuplicateCanary941_X=two'] if duplicate else ['--bogus-DuplicateCanary941']
                    got=self.cli(p,out,raw=flags+['--',PY,'-B','check.py'])
                    self.assertEqual(got[0],2,got[2]);self.assertFalse(got[4]);self.assertIsNone(got[3])
                    self.private(got,['DuplicateCanary941'])
                    self.assertNotIn('Traceback',got[2])

    def test_missing_operands_and_invalid_enrollment_stay_private(self):
        for flags,value in [(['--project','--env','A=project'],'project'),
                            (['--enroll-runner',PY,'--env','A=enroll-runner'],'enroll-runner'),
                            (['--env','--env','A=evidence.py'],'evidence.py')]:
            with self.subTest(flags=flags):
                p,out=self.case();got=self.cli(p,out,raw=flags)
                self.assertEqual(got[0],2,got[2]);self.assertFalse(got[4]);self.assertIsNone(got[3])
                self.private(got,[value])

    def test_check_arguments_are_not_collected_as_wrapper_env(self):
        for boundary in (['--'],[]):
            p,out=self.case("print('childOnlyCanary946')\n")
            got=self.cli(p,out,raw=['--pro',str(p),'--ou',str(out)]+boundary+[PY,'-B','check.py','--env','A=childOnlyCanary946'])
            self.assertEqual(got[0],0,got[2]);self.assertIn('childOnlyCanary946',got[1])

    def test_file_whole_word_rule_and_readable_settings_are_preserved(self):
        p,out=self.case("print('123 12345 PIN_123 8000 true')\n",{'.env':'SECRET_PIN=123\nPORT=8000\nDEBUG=true\n'})
        got=self.cli(p,out)
        self.assertEqual(got[0],0,got[2])
        self.assertIn('12345 PIN_123 8000 true',got[3])
        self.assertIn('<masked SECRET_PIN>',got[3])
        self.assertIn('settings left readable:',got[2])

    def test_final_newline_is_inside_the_confidentiality_boundary(self):
        p,out=self.case("import sys\nsys.stdout.write('last')\n")
        got=self.cli(p,out,['--env','A=last\n'])
        self.assertEqual(got[0],0,got[2]);self.private(got,['last\n'])
        self.assertEqual(got[1],got[3])

    def test_real_exit_codes_survive_literal_word_and_digit_collisions(self):
        for exitcode in (0,1,2,3,7):
            for value in (str(exitcode),'exited %d'%exitcode,'evidence.py'):
                with self.subTest(exitcode=exitcode,value=value):
                    p,out=self.case('import sys\nsys.exit(%d)\n'%exitcode)
                    got=self.cli(p,out,['--env','A='+value])
                    self.assertEqual(got[0],0,got[2]);self.assertTrue(got[4]);self.assertIsNotNone(got[3])
                    self.private(got,[value]);self.facts(got[2],0,True,True,{'exit':exitcode})

    def test_signal_result_remains_recoverable_when_all_digits_are_protected(self):
        for number in (signal.SIGTERM,signal.SIGKILL):
            p,out=self.case('import os\nos.kill(os.getpid(),%d)\n'%number)
            values=list('0123456789')+['signal','SIGTERM','SIGKILL','wrapper','child','v']
            flags=[part for n,value in enumerate(values) for part in ('--env','A%d=%s'%(n,value))]
            got=self.cli(p,out,flags)
            self.assertEqual(got[0],0,got[2]);self.assertTrue(got[4]);self.assertIsNotNone(got[3])
            self.private(got,values)
            self.facts(got[2],0,True,True,{'signal':int(number),'name':signal.Signals(number).name})

    def in_process(self,p,out,flags,patch):
        printed,report=io.StringIO(),io.StringIO()
        with mock.patch.dict(os.environ,{'HOME':self.env['HOME']}),contextlib.redirect_stdout(printed),contextlib.redirect_stderr(report),patch:
            code=evidence.main(['--project',str(p),'--out',str(out)]+flags+['--',PY,'-B','check.py'])
        return code,printed.getvalue(),report.getvalue(),out.read_text() if out.is_file() else None,(p/'ran').exists()

    def test_postlaunch_fail_keeps_known_outcome_and_full_run_state(self):
        for value in ('no-collision948','7','tail\nevidence.py'):
            p,out=self.case('import sys\nsys.exit(7)\n')
            got=self.in_process(p,out,['--env','A='+value],mock.patch.object(evidence,'mask',side_effect=evidence.Fail('tail')))
            self.assertEqual(got[0],3,got[2]);self.assertTrue(got[4]);self.assertIsNone(got[3])
            self.private(got,[value]);self.facts(got[2],3,True,False,{'exit':7})
            if value=='no-collision948':
                self.assertIn('exited 7',got[2]);self.assertIn('the check ran',got[2]);self.assertIn('was not written',got[2])

    def test_spawn_failure_and_retention_failure_keep_distinct_states(self):
        p,out=self.case()
        got=self.in_process(p,out,[],mock.patch.object(evidence.subprocess,'run',side_effect=OSError(13,'Permission denied')))
        self.assertEqual(got[0],1,got[2]);self.assertFalse(got[4]);self.assertIsNone(got[3])
        self.facts(got[2],1,False,False,None)
        p,out=self.case('import sys\nsys.exit(3)\n')
        retain=evidence.childenv.retain
        def retain_then_fail(root):
            retain(root)
            raise evidence.Fail('integrity-fixture')
        got=self.in_process(p,out,[],mock.patch.object(evidence.childenv,'retain',side_effect=retain_then_fail))
        self.assertEqual(got[0],3,got[2]);self.assertTrue(got[4]);self.assertIsNotNone(got[3])
        self.facts(got[2],3,True,True,{'exit':3})

    def test_refusal_leaves_preexisting_evidence_and_reports_no_launch(self):
        p,out=self.case();out.write_text('pre-existing evidence\n')
        got=self.cli(p,out,['--env','BASH_ENV=x'])
        self.assertEqual(got[0],2,got[2]);self.assertFalse(got[4]);self.assertEqual(got[3],'pre-existing evidence\n')
        self.facts(got[2],2,False,False,None)

    def test_child_output_cannot_supply_the_wrappers_result_record(self):
        spoof=dict(v=1,wrapper=0,launched=True,saved=True,child={'exit':0})
        p,out=self.case('import sys\nprint(%r)\nsys.exit(7)\n'%json.dumps(spoof))
        got=self.cli(p,out)
        self.assertEqual(got[0],0,got[2]);self.facts(got[2],0,True,True,{'exit':7})


if __name__=='__main__': unittest.main()
