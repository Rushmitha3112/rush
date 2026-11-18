variable "region" {
  type    = string
  default = "us-east-1"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "alert_email" {
  type        = string
  description = "gets SNS alerts for rejected drops, failed Glue runs and failed loads"
}

variable "glue_workers" {
  type        = number
  default     = 2
  description = "G.1X workers. 2 handles one day (~45k packages) in a few minutes"
}

variable "redshift_base_rpu" {
  type        = number
  default     = 8
  description = "Redshift Serverless minimum. 8 is the floor and is plenty for this volume"
}

variable "build_dir" {
  type        = string
  default     = "../../build"
  description = "output of `make package`"
}
