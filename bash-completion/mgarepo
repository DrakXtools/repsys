# mgarepo(1) completion
#
_cauldron_packages()
{
 COMPREPLY=( $( compgen -W "$(wget -O- \
http://pkgsubmit.mageia.org/data/maintdb.txt 2>/dev/null | \
cut -d ' ' -f 1)" -- $cur ) )
}
 
_mgarepo_actions()
{
 COMPREPLY=( $( compgen -W 'co ci sync \
 submit putsrpm getspec rpmlog getsrpm maintdb create changed \
 authoremail switch upload del up' -- $cur ) )
}
 
_mgarepo()
{
 local cur prev command options i

 COMPREPLY=()
 cur=${COMP_WORDS[COMP_CWORD]}
 if [[ $COMP_CWORD -eq 1 ]] ; then
    if [[ "$cur" == -* ]]; then
      COMPREPLY=( $( compgen -W "--help" -- $cur ) )
    else
      _mgarepo_actions
    fi
 else
    prev=${COMP_WORDS[COMP_CWORD-1]}
    case "$prev" in
      @(get|set))
         _cauldron_packages
         return 0
         ;;
      -@(F))
      _filedir
      return 0
    ;;
    esac

    command=${COMP_WORDS[1]}
    if [[ "$cur" == -* ]]; then
       # possible options for the command
       case $command in
          co)
                  options="-r --distribution \
                           --branch --spec --no-mirror"
          ;;
          ci)
                  options="-m -F"
          ;;
          sync)
                  options="-c --dry-run --download"
          ;;
	  submit)
	          options="-t -l -r -s -i -a --distro --define"
          ;;
          putsrpm) 
                  options="-l -t -b -d -c -s -n"
          ;;
          getsrpm)
                  options="-c -p -v -r -t -P -s -n -l -T -M --strict"
          ;;
	  changed)
                  options="-a -s -M"
          ;;
          esac
          options="$options --help"
          COMPREPLY=( $( compgen -W "$options" -- $cur ) )
    else
         case $command in
         putsrpm)
         _filedir 'src.rpm'
         return 0
         ;;
         @(del|upload))
         _filedir
         return 0
         ;;
         @(co|getspec|rpmlog|getsrpm|changed))
         _cauldron_packages
         return 0
         ;;
         maintdb)
         COMPREPLY=( $( compgen -W "get set" -- $cur ) )
         return 0
         ;;
         @(sync|ci))
         _filedir -d
         return 0
         ;;
         esac
         fi
      fi
}
complete -F _mgarepo $filenames mgarepo 
complete -F _mgarepo $filenames mgarepo-ssh
