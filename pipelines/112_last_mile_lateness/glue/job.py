# Glue entry point. The lastmile package ships as --extra-py-files (see infra/terraform/glue.tf).
from lastmile.transform import main

main()
