from gosubl import gs
from gosubl import mg9
import os
import re
import sublime
import sublime_plugin

DOMAIN = 'GsTest'

TEST_PAT = re.compile(r'^((Test|Example|Benchmark)\w*)')

class GsTestCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.window.active_view())

	def run(self):
		last_test_name = get_last_test_name()

		def f(res, err):

			if err:
				gs.notify(DOMAIN, err)
				return

			mats = {}
			args = {}
			decls = res.get('file_decls', [])
			decls.extend(res.get('pkg_decls', []))
			for d in decls:
				name = d['name']
				prefix, _ =  match_prefix_name(name)
				if prefix and d['kind'] == 'func' and d['repr'] == '':
					mats[True] = prefix
					args[name] = name

			names = sorted(args.keys())
			ents = ['Run all tests and examples']
			if last_test_name != None and last_test_name != 'Run all tests and examples':
				ents.insert(0, last_test_name)

			# TODO: What is the purpose of this for loop? mats.get(k) will never be True
			# which is what it is set at above (mats[True] = prefix)
			for k in ['Test', 'Benchmark', 'Example']:
				if mats.get(k):
					s = 'Run %ss Only' % k
					ents.append(s)
					if k == 'Benchmark':
						args[s] = ['-test.run=none', '-test.bench="%s.*"' % k]
					else:
						args[s] = ['-test.run="%s.*"' % k]

			for k in names:
				ents.append(k)
				if k.startswith('Benchmark'):
					args[k] = ['-test.run=none', '-test.bench="^%s$"' % k]
				else:
					args[k] = ['-test.run="^%s$"' % k]

			def cb(i, win):
				if i >= 0:
					a = args.get(ents[i], [])
					save_last_test_name(ents[i])
					append_extra_test_args(a)
					win.active_view().run_command('gs9o_open', {'run': gs.lst('go', 'test', a)})

			gs.show_quick_panel(ents, cb)

		win, view = gs.win_view(None, self.window)
		if view is None:
			return

		vfn = gs.view_fn(view)
		src = gs.view_src(view)
		pkg_dir = ''
		if view.file_name():
			pkg_dir = os.path.dirname(view.file_name())

		mg9.declarations(vfn, src, pkg_dir, f)

def last_test_hkey():
	return '9o.last_test_name'

def get_last_test_name():
	return gs.aso().get(last_test_hkey())

# TODO: Need to save the test file's path, so we can change to it to run a test if 
# we're not in that directory anymore
def save_last_test_name(test_name):
	gs.aso().set(last_test_hkey(), test_name)
	gs.save_aso()

def append_extra_test_args(a):
	for arg in gs.settings_obj().get('extra_test_args'):
		a.append(arg)

def match_prefix_name(s):
	m = TEST_PAT.match(s)
	return (m.group(2), m.group(1)) if m else ('', '')

def handle_action(view, action):
	fn = view.file_name()
	prefix, name = match_prefix_name(view.substr(view.word(gs.sel(view))))
	ok = prefix and fn and fn.endswith('_test.go')
	if ok:
		if action == 'right-click':
			pat = '^%s.*' % prefix
		else:
			pat = '^%s$' % name

		if prefix == 'Benchmark':
			cmd = ['go', 'test', '-test.run=none', '-test.bench="%s"' % pat]
		else:
			cmd = ['go', 'test', '-test.run="%s"' % pat]

		append_extra_test_args(cmd)
		save_last_test_name(re.sub('[\^\$]','', pat))

		view.run_command('gs9o_open', {'run': cmd})

	return ok
