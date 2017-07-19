if [[ $1 == '-h' ]]; then
  echo "Usage: $0 [-u username] [-p password] [-e email]"
  exit 0;
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

# validate python install
case "$(python --version 2>&1)" in
  *" 3."*)
    echo "Checking Python... installed"
    ;;
  *)
    echo "Checking Python... python 3 not installed, exiting."
    exit 1
    ;;
esac
# check npm 
case "$(npm --version 2>&1)" in
  "4."*)
    echo "Checking npm... installed."
    ;;
  *)
    echo "Checking npm... npm 4.* not installed, exiting."
    exit 1
    ;;
esac

# install pip requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt
echo "Installed Python dependencies..."

# install npm modules 
echo "Installing node modules..."
npm install
echo "Installed node modules..."

# project-specific malarky 
echo "Updating submodules..."
git submodule update --init --recursive
git submodule update --remote
echo "Updated submodules" 

# database malarky
echo "Setting up the database..."
python manage.py migrate
echo "Set up database..."

#You can thank Django for this... if I try to simply pipe input in, it says:
#"Superuser creation skipped due to not running in a TTY." So, here I go.
echo "Creating superuser..."
echo "from django.contrib.auth.models import User;
User.objects.create_superuser('${user}', '${email}', '${password}')" | python manage.py shell
echo "Created superuser with username '${user}', email '${email}' and password '${password}'."

echo "DONE."
