if [[ $1 == '-h' ]]; then
  tput setaf 6; echo "Usage: $0 [-u username] [-p password] [-e email]"
  exit 0;
fi

if [ "$#" -eq 3 ]; then
  u=$1
  p=$2
  e=$3
fi


# check user input, set defaults
while getopts ":u:p:e:" o; do
  case "${o}" in 
    u)  #username
      u=${OPTARG} 
      ;;
    p)  #password
      p=${OPTARG} 
      ;;
    e)  #email
      e=${OPTARG} #not validating e-mail address but I probably should.
      ;;
  esac
done

user="${u:-`whoami`}"
password="${p:-"password"}"
email="${e:-"boom@boom.com"}"

tput setaf 6; echo "Using credentials username: ${user}, password: ${password}, email: ${email}"; tput setaf 7;

# validate python install
case "$(python --version 2>&1)" in
  *" 3."*)
    tput setaf 35; echo "Checking Python... installed"; tput setaf 7;
    ;;
  *)
    tput setaf 1; echo "Checking Python... python 3 not installed, exiting."; tput setaf 7;
    exit 1
    ;;
esac
# check npm 
case "$(npm --version 2>&1)" in
  "4."*)
    tput setaf 35; echo "Checking npm... installed."; tput setaf 7;
    ;;
  *)
    tput setaf 1; echo "Checking npm... npm 4.* not installed, exiting."; tput setaf 7;
    exit 1
    ;;
esac

# install pip requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt
tput setaf 35; echo "Installed Python dependencies..."; tput setaf 7;

# install npm modules 
echo "Installing node modules..."
npm install
tput setaf 35; echo "Installed node modules..."; tput setaf 7;

# project-specific malarky 
echo "Updating submodules..."
git submodule update --init --recursive
git submodule update --remote
tput setaf 35; echo "Updated submodules..."; tput setaf 7;

# database malarky
echo "Setting up the database..."
python manage.py migrate
tput setaf 35; echo "Finished setting up database..."; tput setaf 7;

#You can thank Django for this... if I try to simply pipe input in, it says:
#"Superuser creation skipped due to not running in a TTY." So, here I go.
echo "Creating superuser..."
echo "from django.contrib.auth.models import User;
User.objects.create_superuser('${user}', '${email}', '${password}')" | python manage.py shell

tput setaf 6; echo "Created superuser with username '${user}', email '${email}' and password '${password}'."

tput setaf 34; echo "DONE."
