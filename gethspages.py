import PyHussie
import os
import sys
import urllib
import ConfigParser
import subprocess

###############################################################
#SETTINGS ZONE: everything that has to do with settings lives
#here.
###############################################################

def get_settings(silentr = False, silentm = False):
    """Gets the settings from where they should be: in ~/.gethspages/settings.ini file. If fails, shows an error and quits."""
    parser = ConfigParser.SafeConfigParser()
    parser.read(os.path.expanduser("~/.gethspages/config.ini"))
    settingslist = []    
    try:
        settingslist.append(parser.get("repository", "path"))
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        settingslist.append("")
    try:
        settingslist.append(parser.get("repository", "message"))
    except ConfigParser.NoOptionError:
        if not silentm:
            sys.stderr.write("gethspages: No message is set. Defaulting to 'Homestuck has updated!'. Run gethspages with --set-message argument to set it long-term, or --message to set it for one run.\n")
        settingslist.append("Homestuck has updated!")
    except ConfigParser.NoSectionError:
        if not silentr: 
            sys.stderr.write("gethspages: There is no repository settings in your settings file. Try to set the repository first. Run gethspages with --set-repo argument to set it long-term, or run with -r argument to update the repository once.\n")
        settingslist.append("Homestuck has updated!")
    return settingslist

def make_settings(repositorypath, message = None):
    """Makes settings directory in the homedir and writes settings into the .ini file."""
    if not os.path.exists(os.path.expanduser("~/.gethspages")):
        os.makedirs(os.path.expanduser("~/.gethspages"))
    settout = open(os.path.expanduser("~/.gethspages/config.ini"), "w+")
    settings = ConfigParser.SafeConfigParser()
    settings.add_section("repository")
    settings.set("repository", "path", repositorypath)
    if message:
        settings.set("repository", "message", message)
    settings.write(settout)

def get_absolute_path(settingslist):
    """Gets absolute path of the current act from the settings list that we got from file. Returns a string with an absolute path of an act."""
    rel_path = os.sep.join(settingslist[1])
    abs_path = os.path.expanduser(os.path.join(settingslist[0], rel_path))
    return abs_path

def deduce_next_hussies_page(page):
    """Finds out, what page is next. First, by checking Next Page Link on MSPA, then, if failed, by incrementing the number of the latest page in the repository. If either of this fails, returns None."""
    link = PyHussie.get_parsed_hussies_page(page)[5]
    if link == "":
        link = str(int(page) + 1).zfill(6)
        hussieresponse = urllib.urlopen("http://www.mspaintadventures.com/6/" + link + ".txt")
        readhussie = hussieresponse.read()
        if readhussie.find("404 Not Found") == -1:
            return "\n".join(readhussie.splitlines())
        else:
            return
    return link

def reset_link(translist, hussielist):
    """Resets the link in the page, much like ReHussie, but deeply specialized."""
    translist[5] = hussielist[5]
    return translist

def get_new_pages(root = os.curdir):
    """Gets the new pages from MSPA. Counting from the latest page in the repository. Returns list with parsed pages and their numbers."""
    latest_pagenumber = PyHussie.get_latest_pagenumber(root)[0]
    first_in_row = [reset_link(PyHussie.get_parsed_trans_page(latest_pagenumber, root), PyHussie.get_parsed_hussies_page(latest_pagenumber)), latest_pagenumber]
    pages = [first_in_row]
    latest_pagenumber = deduce_next_hussies_page(latest_pagenumber)
    while latest_pagenumber:
        appendingpage = [PyHussie.get_parsed_hussies_page(latest_pagenumber), latest_pagenumber]
        latest_pagenumber = deduce_next_hussies_page(latest_pagenumber)
        pages.append(appendingpage)
    return pages

###############################################################
#DANGER ZONE: File operations ahead!
###############################################################
def pull_repository(repositorypath):
    """Pulls the specified repository."""
    abspath = os.path.expanduser(repositorypath)
    subprocess.call("git --git-dir=" + abspath + "/.git/ --work-tree=" + abspath + " pull --rebase", shell = True)

def push_repository(repositorypath, message = "Homestuck has updated!"):
    """Pulls the specified repository."""
    abspath = os.path.expanduser(repositorypath)
    subprocess.call("git --git-dir=" + abspath + "/.git/ --work-tree=" + abspath + " add .", shell = True)
    subprocess.call("git --git-dir=" + abspath + "/.git/ --work-tree=" + abspath + r" commit -m '" + message + r"'", shell = True)
    subprocess.call("git --git-dir=" + abspath + "/.git/ --work-tree=" + abspath + " push origin master", shell = True)

def write_pages(pages, root = os.curdir, imgdirname = "img"):
    """Writes the pages to the repository."""
    latest_act = PyHussie.get_latest_pagenumber(root)[1]
    for pagerecord in pages:
        PyHussie.create_page(pagerecord[1], latest_act, PyHussie.assemble_page(pagerecord[0]), root)
        images = PyHussie.get_hussies_images(pagerecord[1])
        for image in images:
            PyHussie.create_image(image, latest_act, root, imgdirname)

def call_collectstatic(repositorypath):
    """Calls collectstatic procedure from sites' manage.py."""
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        sys.stderr.write("gethspages: You have no Django framework. If you are not a Homestuck Translation Project webserver, it's no big deal, but try running with --nocollect, it will save the machine some effort.\n")
        return
    abspath = os.path.expanduser(repositorypath)
    subprocess.call("python " + abspath + "/website/manage.py collectstatic --noinput", shell = True)

def run_update_procedure(repository, message = "Homestuck has updated!", imgdirname = "img", nopush = True, nocollectstatic = True):
    pages = get_new_pages(repository)
    pull_repository(repository)
    write_pages(pages, repository, imgdirname)
    if not nopush:
        push_repository(repository, message)
    if not nocollectstatic:
        call_collectstatic(repository)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(prog = 'gethspages', description = 'GetHSPages: A tool for getting new MS Paint Adventures Homestuck pages into\nHomestuck Translation Project repository.\nFor example:\n> gethspages -r ~/Homestuck-ru\nwill grab new pages from MS Paint Adventures website, along with graphical content,\nadd them to the working directory and push it up to the remote origin.\nThis program supports settings, so you can set the working directory and just call\nthe program.', formatter_class=argparse.RawTextHelpFormatter, epilog = 'COPYRIGHT NOTICE: MS Paint Adventures website and Homestuck belong to Andrew Hussie\nand MS Paint Adventures team. The author of this program makes absolutely no profit\nfrom it, and distributes it freely. Anyone can grab it and do pretty much what they\ndesire with it, within pretty broad limits of the GPL license.\nMade with love by dr. Equivalent the Incredible II and the Homestuck (Russian)\nTranslation Project.')
    
    parser.add_argument("-r", type = str, metavar = "path", help = "use this working directory")
    parser.add_argument("-m", default = get_settings(silentr = True)[1], type = str, metavar = "text", help = "use this commit message")
    parser.add_argument("--nopush", action = "store_true", default = False, help = "do not push to the origin")
    parser.add_argument("--nocollect", action = "store_true", default = False, help = "do not run Django's collectstatic")
    parser.add_argument("--set-repo", type = str, metavar = "path", help = "sets the path of the working directory in the config file")
    parser.add_argument("--set-message", type = str, metavar = "text", help = "sets the commit message in the config file")
    args = parser.parse_args()
    if args.set_repo:
        make_settings(args.set_repo, get_settings(silentr = True)[1])
    if args.set_message:
        try:
            settings = get_settings(silentm = True)
            make_settings(settings[0], args.set_message)
        except ConfigParser.NoSectionError: 
            sys.stderr.write("gethspages: There is no settings in your settings file. Try to set the repository first. Run gethspages with --set-repository argument to set it long-term, or run with -r argument to update the repository once.\n")
    if args.set_repo or args.set_message:
        exit()
    if args.r:
        run_update_procedure(args.r, args.m, nopush = args.nopush, nocollectstatic = args.nocollect)
        exit()
    try:
        run_update_procedure(get_settings()[0], args.m, nopush = args.nopush, nocollectstatic = args.nocollect)
    except IndexError:
        exit()
